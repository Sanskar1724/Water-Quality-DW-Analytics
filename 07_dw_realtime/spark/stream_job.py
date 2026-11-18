"""
Spark Structured Streaming job (runs inside the wq_spark container).

Kafka topic (replayed WQP events, JSON)  ->  parse + validate  ->  derived measures (exceedance, high risk, alert level)
  ->  (1) every valid event to ClickHouse wq_rt.events
  ->  (2) 1-hour event-time window aggregates (with watermark) to ClickHouse wq_rt.window_agg
  ->  (3) invalid events to ClickHouse wq_rt.rejected
Micro-batch trigger: every 5 seconds.
"""
import os, json, urllib.request, base64
from pyspark.sql import SparkSession, functions as F, types as T

KAFKA = os.environ.get('KAFKA_BOOTSTRAP', 'kafka:29092')
TOPIC = os.environ.get('KAFKA_TOPIC', 'wq.results.replay')
CH_URL = os.environ.get('CLICKHOUSE_URL', 'http://clickhouse:8123')
CH_AUTH = base64.b64encode(f"{os.environ.get('CLICKHOUSE_USER', 'wq')}:{os.environ.get('CLICKHOUSE_PASSWORD', '')}".encode()).decode()

# Event JSON schema (documented in 07_dw_realtime/GUIDE.md)
SCHEMA = T.StructType([
    T.StructField('event_id', T.StringType()), T.StructField('site_id', T.StringType()),
    T.StructField('state', T.StringType()), T.StructField('region', T.StringType()),
    T.StructField('organization', T.StringType()), T.StructField('characteristic', T.StringType()),
    T.StructField('result_value', T.DoubleType()), T.StructField('unit', T.StringType()),
    T.StructField('event_time', T.StringType()), T.StructField('latitude', T.DoubleType()),
    T.StructField('longitude', T.DoubleType()), T.StructField('produced_at', T.StringType()),
    T.StructField('simulation', T.BooleanType()),
])
# Physical validity ranges (same as Step 2) and thresholds (Step 2, documented)
RANGE = {'Temperature, water': (-5, 50), 'Dissolved oxygen (DO)': (0, 25), 'pH': (0, 14),
         'Turbidity': (0, 10000), 'Conductivity': (0, 200000), 'Nitrate': (0, 100)}


def ch_insert(table, rows):
    """Insert JSON rows into ClickHouse over its HTTP interface (no extra Python packages needed)."""
    if not rows: return
    body = '\n'.join(rows).encode()
    req = urllib.request.Request(f"{CH_URL}/?query=INSERT%20INTO%20wq_rt.{table}%20FORMAT%20JSONEachRow"
                                 "&date_time_input_format=best_effort", data=body, method='POST',
                                 headers={'Authorization': f'Basic {CH_AUTH}'})
    urllib.request.urlopen(req, timeout=60).read()


spark = SparkSession.builder.appName('wq-realtime-replay').getOrCreate()
spark.sparkContext.setLogLevel('WARN')

raw = (spark.readStream.format('kafka').option('kafka.bootstrap.servers', KAFKA).option('subscribe', TOPIC)
       .option('startingOffsets', 'earliest').option('failOnDataLoss', 'false').option('maxOffsetsPerTrigger', 20000).load()
       .select(F.col('value').cast('string').alias('raw_value')))

parsed = raw.withColumn('e', F.from_json('raw_value', SCHEMA)).select('raw_value', 'e.*') \
            .withColumn('event_ts', F.to_timestamp('event_time')) \
            .withColumn('produced_ts', F.to_timestamp('produced_at'))

lo = F.create_map(*[x for k, (a, b) in RANGE.items() for x in (F.lit(k), F.lit(float(a)))])
hi = F.create_map(*[x for k, (a, b) in RANGE.items() for x in (F.lit(k), F.lit(float(b)))])
reason = (F.when(F.col('event_id').isNull(), 'Unparseable JSON / missing event_id')
           .when(F.col('event_ts').isNull(), 'Missing or invalid event_time')
           .when(F.col('site_id').isNull(), 'Missing site_id')
           .when(~F.col('characteristic').isin(list(RANGE)), 'Unknown characteristic')
           .when(F.col('result_value').isNull(), 'Missing value')
           .when((F.col('result_value') < lo[F.col('characteristic')]) | (F.col('result_value') > hi[F.col('characteristic')]),
                 'Physically impossible value'))
checked = parsed.withColumn('reject_reason', reason)

c, v = F.col('characteristic'), F.col('result_value')
exceed = (F.when(c == 'Dissolved oxygen (DO)', v < 5).when(c == 'pH', (v < 6.5) | (v > 9)).when(c == 'Nitrate', v > 10)
           .when(c == 'Temperature, water', v > 28).when(c == 'Turbidity', v > 25).when(c == 'Conductivity', v > 1500)).cast('int')
high = (F.when(c == 'Dissolved oxygen (DO)', v < 2).when(c == 'pH', (v < 6) | (v > 9.5)).when(c == 'Nitrate', v > 20)
         .when(c == 'Temperature, water', v > 32).when(c == 'Turbidity', v > 100).when(c == 'Conductivity', v > 3000)).cast('int')
valid = (checked.where(F.col('reject_reason').isNull())
         .withColumn('exceedance_flag', exceed).withColumn('high_risk_flag', high)
         .withColumn('alert_level', F.when(F.col('high_risk_flag') == 1, 'HIGH RISK').when(F.col('exceedance_flag') == 1, 'EXCEEDANCE').otherwise('OK'))
         .withColumn('processed_at', F.current_timestamp()))

EVENT_COLS = ['event_id', 'site_id', 'state', 'region', 'organization', 'characteristic', 'result_value', 'unit',
              'event_time', 'exceedance_flag', 'high_risk_flag', 'alert_level', 'latitude', 'longitude', 'produced_at', 'processed_at']


def write_events(df, batch_id):
    out = df.select(*[F.date_format('event_ts', 'yyyy-MM-dd HH:mm:ss').alias('event_time') if x == 'event_time'
                      else F.date_format('produced_ts', 'yyyy-MM-dd HH:mm:ss.SSS').alias('produced_at') if x == 'produced_at'
                      else F.date_format('processed_at', 'yyyy-MM-dd HH:mm:ss.SSS').alias('processed_at') if x == 'processed_at'
                      else F.col(x) for x in EVENT_COLS])
    rows = out.toJSON().collect(); ch_insert('events', rows)
    print(f'[batch {batch_id}] events written: {len(rows)}', flush=True)


def write_rejected(df, batch_id):
    rows = [json.dumps({'raw_value': r.raw_value or '', 'reason': r.reject_reason})
            for r in df.select('raw_value', 'reject_reason').collect()]
    ch_insert('rejected', rows)
    if rows: print(f'[batch {batch_id}] rejected: {len(rows)}', flush=True)


def write_windows(df, batch_id):
    out = df.select(F.date_format('window.start', 'yyyy-MM-dd HH:mm:ss').alias('window_start'),
                    F.date_format('window.end', 'yyyy-MM-dd HH:mm:ss').alias('window_end'),
                    'characteristic', F.coalesce('region', F.lit('Unknown')).alias('region'), 'results', 'avg_value',
                    'max_value', 'min_value', 'exceedances', 'high_risk')
    ch_insert('window_agg', out.toJSON().collect())


q1 = (valid.writeStream.foreachBatch(write_events).option('checkpointLocation', '/tmp/checkpoints/events')
      .trigger(processingTime='5 seconds').start())
q2 = (checked.where(F.col('reject_reason').isNotNull()).writeStream.foreachBatch(write_rejected)
      .option('checkpointLocation', '/tmp/checkpoints/rejected').trigger(processingTime='5 seconds').start())
windows = (valid.withWatermark('event_ts', '2 hours')
           .groupBy(F.window('event_ts', '1 hour'), 'characteristic', 'region')
           .agg(F.count('*').alias('results'), F.avg('result_value').alias('avg_value'), F.max('result_value').alias('max_value'),
                F.min('result_value').alias('min_value'), F.sum('exceedance_flag').alias('exceedances'), F.sum('high_risk_flag').alias('high_risk')))
q3 = (windows.writeStream.outputMode('update').foreachBatch(write_windows).option('checkpointLocation', '/tmp/checkpoints/windows')
      .trigger(processingTime='5 seconds').start())
print(f'Streaming from Kafka topic {TOPIC} at {KAFKA} into ClickHouse {CH_URL} (SIMULATION replay)', flush=True)
spark.streams.awaitAnyTermination()

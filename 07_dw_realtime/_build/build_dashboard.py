"""Generates grafana/dashboards/wq_realtime.json (8 required live KPIs + banner + map)."""
import json
from pathlib import Path
DS = {'type': 'grafana-clickhouse-datasource', 'uid': 'wq-clickhouse'}
OUT = Path(__file__).resolve().parents[1] / 'grafana' / 'dashboards' / 'wq_realtime.json'
panels, pid = [], [0]

def q(sql, ts=False):
    return [{'refId': 'A', 'datasource': DS, 'editorType': 'sql', 'format': 0 if ts else 1,
             'queryType': 'timeseries' if ts else 'table', 'rawSql': ' '.join(sql.split())}]

def panel(kind, title, x, y, w, h, sql=None, ts=False, desc='', **extra):
    pid[0] += 1
    p = {'id': pid[0], 'type': kind, 'title': title, 'description': desc, 'gridPos': {'x': x, 'y': y, 'w': w, 'h': h}, 'datasource': DS}
    if sql: p['targets'] = q(sql, ts)
    p.update(extra); panels.append(p)

def stat(title, x, sql, color='blue', desc='', unit='short'):
    panel('stat', title, x, 3, 4, 4, sql, desc=desc,
          fieldConfig={'defaults': {'unit': unit, 'color': {'mode': 'fixed', 'fixedColor': color}}, 'overrides': []},
          options={'colorMode': 'background', 'graphMode': 'none', 'reduceOptions': {'calcs': ['lastNotNull'], 'values': False}})

E = 'wq_rt.events'
panel('text', '', 0, 0, 24, 3, options={'mode': 'markdown', 'content':
      '## 🔴 SIMULATION: historical Water Quality Portal results (December 2025) **replayed in time order** as live events\n'
      'Python producer → **Kafka** → **Spark Structured Streaming** (validate, derive exceedance / high-risk, 1-hour event-time windows) → **ClickHouse** → **Grafana** (refresh 5 s). Not a live feed.'})
stat('Results received', 0, f'SELECT count() FROM {E}', 'blue', 'All validated events stored in ClickHouse')
stat('KPI 1 · Results / minute (now)', 4, f'SELECT count() FROM {E} WHERE ingested_at > now64(3) - INTERVAL 60 SECOND', 'purple', 'Events ingested in the last 60 seconds of replay')
stat('KPI 4 · Exceedances', 8, f'SELECT sum(exceedance_flag) FROM {E}', 'orange', 'Results breaking the documented exceedance threshold')
stat('KPI 3 · High-risk observations', 12, f'SELECT sum(high_risk_flag) FROM {E}', 'red', 'Results breaking the stricter high-risk threshold')
stat('Rejected by validation', 16, 'SELECT count() FROM wq_rt.rejected', 'dark-red', 'Events that failed Spark validation rules')
stat('Pipeline latency (median, s)', 20, f"SELECT round(quantile(0.5)(dateDiff('millisecond', produced_at, ingested_at)) / 1000, 2) FROM {E} WHERE ingested_at > now64(3) - INTERVAL 5 MINUTE",
     'green', 'Producer send → stored in ClickHouse', unit='s')

panel('timeseries', 'KPI 1 · Results per minute during replay (10-second buckets × 6)', 0, 7, 12, 8,
      f"SELECT toStartOfInterval(ingested_at, INTERVAL 10 SECOND) AS time, count() * 6 AS results_per_minute FROM {E} "
      "WHERE ingested_at > now64(3) - INTERVAL 30 MINUTE GROUP BY time ORDER BY time", ts=True,
      fieldConfig={'defaults': {'custom': {'drawStyle': 'bars', 'fillOpacity': 60}}, 'overrides': []})
panel('timeseries', 'KPI 4 · Exceedances per 10 s by parameter', 12, 7, 12, 8,
      f"SELECT toStartOfInterval(ingested_at, INTERVAL 10 SECOND) AS time, characteristic, sum(exceedance_flag) AS exceedances FROM {E} "
      "WHERE ingested_at > now64(3) - INTERVAL 30 MINUTE GROUP BY time, characteristic ORDER BY time", ts=True)

panel('table', 'KPI 2 · Current parameter values (latest replayed result)', 0, 15, 9, 8,
      f"SELECT characteristic AS parameter, round(argMax(result_value, (event_time, ingested_at)), 2) AS latest_value, any(unit) AS unit, "
      f"argMax(site_id, (event_time, ingested_at)) AS site, max(event_time) AS sample_time FROM {E} GROUP BY characteristic ORDER BY parameter")
panel('bargauge', 'KPI 6 · Parameter coverage (results and sites)', 9, 15, 7, 8,
      f"SELECT characteristic, count() AS results FROM {E} GROUP BY characteristic ORDER BY results DESC",
      options={'orientation': 'horizontal', 'displayMode': 'gradient', 'reduceOptions': {'calcs': ['lastNotNull'], 'values': True}})
panel('table', 'KPI 5 · Top monitored sites', 16, 15, 8, 8,
      f"SELECT site_id, any(state) AS state, count() AS results, uniqExact(characteristic) AS parameters, "
      f"round(100 * avg(exceedance_flag), 1) AS exceedance_pct FROM {E} GROUP BY site_id ORDER BY results DESC LIMIT 15")

panel('table', 'KPI 7 · Poor-quality sites (≥ 10 results, ≥ 50% exceedance)', 0, 23, 12, 9,
      f"SELECT site_id, any(state) AS state, count() AS results, sum(exceedance_flag) AS exceedances, "
      f"round(100 * avg(exceedance_flag), 1) AS exceedance_pct, groupUniqArray(characteristic) AS parameters FROM {E} "
      "GROUP BY site_id HAVING results >= 10 AND exceedance_pct >= 50 ORDER BY exceedance_pct DESC, results DESC LIMIT 20")
panel('table', 'KPI 8 · ALERTS: latest high-risk results', 12, 23, 12, 9,
      f"SELECT ingested_at AS received, event_time AS sampled, site_id, state, characteristic, round(result_value, 2) AS value, unit, alert_level "
      f"FROM {E} WHERE high_risk_flag = 1 ORDER BY ingested_at DESC LIMIT 25",
      fieldConfig={'defaults': {}, 'overrides': [{'matcher': {'id': 'byName', 'options': 'alert_level'},
                                                  'properties': [{'id': 'custom.cellOptions', 'value': {'type': 'color-background'}},
                                                                 {'id': 'color', 'value': {'mode': 'fixed', 'fixedColor': 'red'}}]}]})

panel('timeseries', 'Spark event-time windows: exceedance % per sample hour (watermarked aggregates)', 0, 32, 14, 9,
      "SELECT window_start AS time, characteristic, round(100 * sum(exceedances) / sum(results), 1) AS exceedance_pct "
      "FROM wq_rt.window_agg FINAL GROUP BY time, characteristic ORDER BY time", ts=True)
panel('geomap', 'High-risk alert locations', 14, 32, 10, 9,
      f"SELECT site_id, any(latitude) AS latitude, any(longitude) AS longitude, count() AS alerts FROM {E} "
      "WHERE high_risk_flag = 1 AND latitude IS NOT NULL GROUP BY site_id",
      options={'view': {'id': 'coords', 'lat': 39, 'lon': -97, 'zoom': 3},
               'layers': [{'type': 'markers', 'config': {'style': {'color': {'fixed': 'red'}, 'size': {'fixed': 4}}},
                           'location': {'mode': 'coords', 'latitude': 'latitude', 'longitude': 'longitude'}}]})

dash = {'uid': 'wq-realtime', 'title': 'Water Quality · Real-Time Replay (SIMULATION)', 'tags': ['water-quality', 'realtime'],
        'timezone': 'browser', 'refresh': '5s', 'time': {'from': 'now-30m', 'to': 'now'}, 'schemaVersion': 39, 'version': 1, 'panels': panels}
OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(dash, indent=2), encoding='utf-8')
print('written', OUT, len(panels), 'panels')

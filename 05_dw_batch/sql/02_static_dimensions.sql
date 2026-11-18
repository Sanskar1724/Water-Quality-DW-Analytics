-- Static dimensions: loaded once at the initial load (they do not depend on the data batch)

-- DimDate: every calendar day of the study period (2024-01-01 … 2025-12-31)
INSERT INTO dw.dim_date
SELECT to_char(d, 'YYYYMMDD')::INT, d::DATE, EXTRACT(DAY FROM d), trim(to_char(d, 'Day')), EXTRACT(ISODOW FROM d),
       EXTRACT(ISODOW FROM d) IN (6, 7), EXTRACT(WEEK FROM d), EXTRACT(MONTH FROM d), trim(to_char(d, 'Month')),
       to_char(d, 'YYYY-MM'), EXTRACT(QUARTER FROM d), EXTRACT(YEAR FROM d),
       CASE WHEN EXTRACT(MONTH FROM d) IN (12, 1, 2) THEN 'Winter' WHEN EXTRACT(MONTH FROM d) IN (3, 4, 5) THEN 'Spring'
            WHEN EXTRACT(MONTH FROM d) IN (6, 7, 8) THEN 'Summer' ELSE 'Autumn' END
FROM generate_series(DATE '2024-01-01', DATE '2025-12-31', INTERVAL '1 day') AS d
ON CONFLICT DO NOTHING;

-- DimTime: 24 hours + "Not Reported"
INSERT INTO dw.dim_time
SELECT h, h, CASE WHEN h < 6 THEN 'Night' WHEN h < 12 THEN 'Morning' WHEN h < 18 THEN 'Afternoon' ELSE 'Evening' END
FROM generate_series(0, 23) AS h
ON CONFLICT DO NOTHING;
INSERT INTO dw.dim_time VALUES (-1, NULL, 'Not Reported') ON CONFLICT DO NOTHING;

-- DimCharacteristic: the 6 parameters with their documented thresholds (Step 2)
INSERT INTO dw.dim_characteristic (characteristic_name, short_name, parameter_group, standard_unit, exceedance_rule, high_risk_rule, threshold_source) VALUES
 ('Temperature, water',    'Temperature',      'Physical', '°C',        '> 28 °C',               '> 32 °C',               'Project threshold (aquatic-life heat stress)'),
 ('Dissolved oxygen (DO)', 'Dissolved oxygen', 'Chemical', 'mg/L',      '< 5 mg/L',              '< 2 mg/L (hypoxia)',    'EPA aquatic-life DO criteria'),
 ('pH',                    'pH',               'Chemical', 'pH units',  '< 6.5 or > 9.0',        '< 6.0 or > 9.5',        'EPA national criterion 6.5–9, margin = project'),
 ('Turbidity',             'Turbidity',        'Physical', 'NTU',       '> 25 NTU',              '> 100 NTU',             'Project threshold'),
 ('Conductivity',          'Conductivity',     'Physical', 'µS/cm',     '> 1,500 µS/cm',         '> 3,000 µS/cm',         'Project threshold'),
 ('Nitrate',               'Nitrate',          'Nutrient', 'mg/L as N', '> 10 mg/L as N',        '> 20 mg/L as N',        'EPA drinking-water MCL 10 mg/L, 20 = project')
ON CONFLICT DO NOTHING;

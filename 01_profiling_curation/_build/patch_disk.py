"""Disk-saving patch: drop each intermediate table once the next exists; build model features via small lookup tables."""
p = __file__.replace('patch_disk.py', 'build_curation_nb.py')
s = open(p, encoding='utf8').read()
def R(a, b):
    global s
    assert a in s, 'NOT FOUND: ' + a[:70]
    s = s.replace(a, b, 1)

R("FROM p''')\nus = q(", "FROM p''')\ncon.execute('DROP TABLE b')   # free disk: previous stage no longer needed\nus = q(")
R("FROM v1''')\ncon.execute('''\nCREATE OR REPLACE TABLE v2 AS", "FROM v1''')\ncon.execute('DROP TABLE v1')\ncon.execute('''\nCREATE OR REPLACE TABLE v2 AS")
R("FROM t''')\ntb = q(", "FROM t''')\ncon.execute('DROP TABLE v2')\ntb = q(")
R("FROM v3''')\nsites = q(", "FROM v3''')\ncon.execute('DROP TABLE v3')\nsites = q(")
R("FROM v4 LEFT JOIN fz USING (param)''')", "FROM v4 LEFT JOIN fz USING (param)''')\ncon.execute('DROP TABLE v4')")
R("FROM v5''')\ncon.execute('CREATE OR REPLACE TABLE v6 AS SELECT *, exclusion_reason IS NULL AS analysis_ready FROM v6')",
  "FROM v5''')\ncon.execute('DROP TABLE v5')\ncon.execute('ALTER TABLE v6 ADD COLUMN analysis_ready BOOLEAN')\ncon.execute('UPDATE v6 SET analysis_ready = exclusion_reason IS NULL')")
R("FROM v6''')\nrates = q(", "FROM v6''')\ncon.execute('DROP TABLE v6')\nrates = q(")
R("FROM w LEFT JOIN site_wt USING (site) LEFT JOIN act_eq USING (act_id) LEFT JOIN act_cm USING (act_id)''')",
  "FROM w LEFT JOIN site_wt USING (site) LEFT JOIN act_eq USING (act_id) LEFT JOIN act_cm USING (act_id)''')\ncon.execute('DROP TABLE v7')")
# lighter feature encoding: small dictionaries + joins instead of 11 window sorts
R('''sel = ', '.join(f"dense_rank() OVER (ORDER BY coalesce({e}, 'NA')) - 1 AS {k}" for k, e in FEATS.items())
X_all = q(f\'\'\'SELECT rid, {sel}, water_type_l1, equipment_l1, time_band_l1, is_summary FROM v8\'\'\').sort_values('rid').reset_index(drop=True)''',
  '''for k, e in FEATS.items():   # one small lookup table per feature: value -> integer code
    con.execute(f"CREATE OR REPLACE TEMP TABLE d_{k} AS SELECT v, (row_number() OVER (ORDER BY v) - 1)::INT AS c FROM (SELECT DISTINCT coalesce({e}, 'NA') AS v FROM v8)")
sel = ', '.join(f'd_{k}.c AS {k}' for k in FEATS)
joins = ' '.join(f"JOIN d_{k} ON d_{k}.v = coalesce({e}, 'NA')" for k, e in FEATS.items())
X_all = q(f\'\'\'SELECT rid, {sel}, water_type_l1, equipment_l1, time_band_l1, is_summary FROM v8 {joins}\'\'\').sort_values('rid').reset_index(drop=True)''')
R("FROM v8 LEFT JOIN fill_water_type fw USING (rid) LEFT JOIN fill_equipment fe USING (rid) LEFT JOIN fill_time_band ft USING (rid)''')",
  "FROM v8 LEFT JOIN fill_water_type fw USING (rid) LEFT JOIN fill_equipment fe USING (rid) LEFT JOIN fill_time_band ft USING (rid)''')\ncon.execute('DROP TABLE v8')")
R("con.close()\n\"\"\")", "con.close()\nDB.unlink(missing_ok=True)   # the work database is temporary; the Parquet file is the output\n\"\"\")")
open(p, 'w', encoding='utf8').write(s)
print('patched')

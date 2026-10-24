-- Executable SQLite prototype schema. Foreign keys and composite uniqueness preserve grain.
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS geography (
 geography_id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS indicator (
 indicator_id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
 unit TEXT NOT NULL, aggregation TEXT NOT NULL, frequency TEXT NOT NULL CHECK(frequency='monthly')
);
CREATE TABLE IF NOT EXISTS source_vintage (
 vintage_id INTEGER PRIMARY KEY, filename TEXT NOT NULL, sha256 TEXT NOT NULL UNIQUE,
 ingested_at TEXT NOT NULL, release_date TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS observation (
 observation_id INTEGER PRIMARY KEY,
 indicator_id INTEGER NOT NULL REFERENCES indicator,
 geography_id INTEGER NOT NULL REFERENCES geography,
 reference_month TEXT NOT NULL CHECK(substr(reference_month,9,2)='01'),
 vintage_id INTEGER NOT NULL REFERENCES source_vintage,
 value REAL NOT NULL, source_locator TEXT NOT NULL,
 available_at TEXT, availability_basis TEXT NOT NULL,
 UNIQUE(indicator_id,geography_id,reference_month,vintage_id)
);
CREATE TABLE IF NOT EXISTS dataset_snapshot (
 snapshot_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, start_month TEXT NOT NULL,
 end_month TEXT NOT NULL, manifest_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshot_observation (
 snapshot_id TEXT NOT NULL REFERENCES dataset_snapshot,
 observation_id INTEGER NOT NULL REFERENCES observation,
 PRIMARY KEY(snapshot_id,observation_id)
);
CREATE TABLE IF NOT EXISTS model_spec (
 model_id TEXT PRIMARY KEY, family TEXT NOT NULL, specification_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS model_run (
 run_id TEXT PRIMARY KEY, model_id TEXT NOT NULL REFERENCES model_spec,
 snapshot_id TEXT NOT NULL REFERENCES dataset_snapshot,
 created_at TEXT NOT NULL, forecast_origin TEXT NOT NULL, training_start TEXT NOT NULL,
 training_end TEXT NOT NULL, phase TEXT NOT NULL CHECK(phase IN ('validation','test','production')),
 status TEXT NOT NULL CHECK(status IN ('success','failed')), diagnostics_json TEXT,
 UNIQUE(model_id,snapshot_id,forecast_origin,phase)
);
CREATE TABLE IF NOT EXISTS forecast (
 forecast_id INTEGER PRIMARY KEY, run_id TEXT NOT NULL REFERENCES model_run,
 target_indicator_id INTEGER NOT NULL REFERENCES indicator,
 geography_id INTEGER NOT NULL REFERENCES geography,
 target_month TEXT NOT NULL, horizon INTEGER NOT NULL CHECK(horizon BETWEEN 1 AND 3),
 estimate REAL NOT NULL, lower_95 REAL, upper_95 REAL,
 CHECK(lower_95 IS NULL OR upper_95 >= lower_95),
 UNIQUE(run_id,target_indicator_id,geography_id,target_month),
 UNIQUE(run_id,target_indicator_id,geography_id,horizon)
);
CREATE TABLE IF NOT EXISTS forecast_evaluation (
 forecast_id INTEGER NOT NULL REFERENCES forecast,
 actual_observation_id INTEGER NOT NULL REFERENCES observation,
 error REAL NOT NULL, absolute_error REAL NOT NULL CHECK(absolute_error>=0),
 squared_error REAL NOT NULL CHECK(squared_error>=0),
 PRIMARY KEY(forecast_id,actual_observation_id)
);

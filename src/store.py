"""Populate normalized prototype storage from notebook exports, preserving vintages."""
import sqlite3
import json
import hashlib
from datetime import datetime, timezone
import pandas as pd
from src.prepare import ROOT

def load_database():
    db = sqlite3.connect(ROOT/'database/inflation.db')
    db.executescript((ROOT/'database/schema.sql').read_text())
    now = datetime.now(timezone.utc).isoformat()
    monthly_path = ROOT/'data/processed/monthly.csv'
    df = pd.read_csv(monthly_path,parse_dates=['date']).set_index('date')
    manifest = json.loads((ROOT/'data/processed/manifest.json').read_text())
    snapshot = hashlib.sha256(monthly_path.read_bytes()+(ROOT/'data/processed/manifest.json').read_bytes()).hexdigest()
    db.execute('INSERT OR IGNORE INTO geography VALUES (1,?,?)',('PH','Philippines'))
    definitions = [
      (1,'inflation','National all-items year-on-year inflation','percent','year-on-year change'),
      (2,'exchange_rate','PHP per US dollar','PHP/USD','monthly average'),
      (3,'m3','Broad money M3','million PHP','end of period'),
      (4,'policy_rate','BSP policy RRP rate','percent','last decision in month; carried forward')]
    for id_,code,name,unit,agg in definitions:
        db.execute('INSERT OR IGNORE INTO indicator VALUES (?,?,?,?,?,?)',(id_,code,name,unit,agg,'monthly'))
    vintages = {}
    for f in manifest['files']:
        db.execute('INSERT OR IGNORE INTO source_vintage(filename,sha256,ingested_at,notes) VALUES (?,?,?,?)',
            (f['file'],f['sha256'],now,'Uploaded vintage; original release date unknown'))
        vintages[f['file']] = db.execute('SELECT vintage_id FROM source_vintage WHERE sha256=?',(f['sha256'],)).fetchone()[0]
    db.execute('INSERT OR IGNORE INTO dataset_snapshot VALUES (?,?,?,?,?)',
        (snapshot,now,str(df.index[0].date()),str(df.index[-1].date()),json.dumps(manifest)))
    actual_ids = {}
    for month,row in df.iterrows():
        for id_,code,*_ in definitions:
            if pd.isna(row[code]):
                continue
            if code=='inflation':
                file = 'Dataset-11995-2018.csv' if month.year<=2018 else 'Dataset-12019-2026.csv'
                locator = 'PHILIPPINES / 0 - ALL ITEMS / '+month.strftime('%Y %b')
            else:
                file,locator = {'exchange_rate':('pesodollar.xlsx','monthly / Average'),
                               'm3':('dcs_srf.xlsx','July 2026 / level row 25'),
                               'policy_rate':('MonetaryPolicyDecisions.xlsx','Sheet1 / latest numeric decision through month')}[code]
            key = (id_,1,str(month.date()),vintages[file])
            db.execute('INSERT OR IGNORE INTO observation(indicator_id,geography_id,reference_month,vintage_id,value,source_locator,availability_basis) VALUES (?,?,?,?,?,?,?)',
                (*key,float(row[code]),locator,'unknown original publication date'))
            obs = db.execute('SELECT observation_id FROM observation WHERE indicator_id=? AND geography_id=? AND reference_month=? AND vintage_id=?',key).fetchone()[0]
            db.execute('INSERT OR IGNORE INTO snapshot_observation VALUES (?,?)',(snapshot,obs))
            if code=='inflation': actual_ids[str(month.date())] = obs
    meta = json.loads((ROOT/'artifacts/model.json').read_text())
    model_ids = {}
    for name,spec in meta['specifications'].items():
        specification = json.dumps(spec,sort_keys=True)
        model_ids[name] = name+'|'+hashlib.sha256(specification.encode()).hexdigest()[:16]
        db.execute('INSERT OR IGNORE INTO model_spec VALUES (?,?,?)',(model_ids[name],spec['family'],specification))
    results = pd.read_csv(ROOT/'artifacts/backtest.csv')
    run_metadata = json.loads((ROOT/'artifacts/runs.json').read_text())
    run_metadata.append({'model':meta['selected_model'],'origin':meta['forecast_origin'],'phase':'production','status':'success',**meta['production_diagnostics']})
    # IDs include specification hash so future specification edits cannot collide.
    run_ids = {}
    for run in run_metadata:
        name,origin,phase = run['model'],run['origin'],run['phase']
        run_id = hashlib.sha256(f'{snapshot}|{model_ids[name]}|{origin}|{phase}'.encode()).hexdigest()
        run_ids[(name,origin,phase)] = run_id
        db.execute('INSERT OR IGNORE INTO model_run VALUES (?,?,?,?,?,?,?,?,?,?)',
            (run_id,model_ids[name],snapshot,now,origin,meta['training_start'],origin,phase,run['status'],json.dumps(run)))
    production = pd.read_csv(ROOT/'artifacts/forecast.csv')
    production['model'],production['origin'],production['phase'] = meta['selected_model'],meta['forecast_origin'],'production'
    for r in pd.concat([results,production],ignore_index=True).to_dict('records'):
        assert pd.Timestamp(r['target']) == pd.Timestamp(r['origin'])+pd.DateOffset(months=int(r['horizon']))
        rid = run_ids[(r['model'],r['origin'],r['phase'])]
        clean = lambda v: None if pd.isna(v) else float(v)
        db.execute('INSERT OR IGNORE INTO forecast(run_id,target_indicator_id,geography_id,target_month,horizon,estimate,lower_95,upper_95) VALUES (?,1,1,?,?,?,?,?)',
            (rid,r['target'],int(r['horizon']),float(r['estimate']),clean(r['lower_95']),clean(r['upper_95'])))
        fid = db.execute('SELECT forecast_id FROM forecast WHERE run_id=? AND target_month=?',(rid,r['target'])).fetchone()[0]
        if r['target'] in actual_ids:
            actual = df.loc[r['target'],'inflation']
            e = float(r['estimate']-actual)
            db.execute('INSERT OR IGNORE INTO forecast_evaluation VALUES (?,?,?,?,?)',(fid,actual_ids[r['target']],e,abs(e),e*e))
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    db.commit()
    print('Stored',db.execute('SELECT COUNT(*) FROM observation').fetchone()[0],'observations and',db.execute('SELECT COUNT(*) FROM forecast').fetchone()[0],'forecasts.')
    db.close()

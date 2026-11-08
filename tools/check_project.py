from pathlib import Path
import sys
import sqlite3
import hashlib
import json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.packages'))
sys.path.insert(0,str(ROOT))
import pandas as pd
import numpy as np

data=pd.read_csv(ROOT/'data/processed/monthly.csv',parse_dates=['date']).set_index('date')
primary=data.loc[:'2026-07-01']
assert len(primary)==199 and primary.index.is_unique
assert primary[['inflation','exchange_rate','m3','policy_rate']].notna().all().all()
for f in json.loads((ROOT/'data/processed/manifest.json').read_text())['files']:
    assert hashlib.sha256((ROOT/'data/raw'/f['file']).read_bytes()).hexdigest()==f['sha256']
with sqlite3.connect(ROOT/'database/inflation.db') as db:
    db.execute('PRAGMA foreign_keys=ON')
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    assert not db.execute('SELECT indicator_id,geography_id,reference_month,vintage_id,COUNT(*) FROM observation GROUP BY 1,2,3,4 HAVING COUNT(*)>1').fetchall()
    forecasts=pd.read_sql_query('SELECT f.*,r.forecast_origin FROM forecast f JOIN model_run r USING(run_id)',db)
    for r in forecasts.itertuples():
        assert pd.Timestamp(r.target_month)==pd.Timestamp(r.forecast_origin)+pd.DateOffset(months=r.horizon)
    evaluations=pd.read_sql_query('SELECT f.estimate,o.value,e.error,e.absolute_error,e.squared_error FROM forecast_evaluation e JOIN forecast f USING(forecast_id) JOIN observation o ON o.observation_id=e.actual_observation_id',db)
    assert np.allclose(evaluations.error,evaluations.estimate-evaluations.value)
    assert np.allclose(evaluations.absolute_error,abs(evaluations.error))
    assert np.allclose(evaluations.squared_error,evaluations.error**2)
    # Prove the fact-grain constraint rejects duplicates.
    try:
        db.execute('INSERT INTO observation(indicator_id,geography_id,reference_month,vintage_id,value,source_locator,availability_basis) SELECT indicator_id,geography_id,reference_month,vintage_id,value,source_locator,availability_basis FROM observation LIMIT 1')
        raise AssertionError('Duplicate fact incorrectly accepted')
    except sqlite3.IntegrityError:
        pass
    db.rollback()
results=pd.read_csv(ROOT/'artifacts/backtest.csv')
counts=results.groupby(['phase','model','horizon']).size()
assert counts.loc['validation'].eq(12).all()
assert counts.loc['test'].eq(24).all()
assert results.model.nunique()==8
for phase in ['validation','test']:
    sets=results[results.phase==phase].groupby(['model','horizon']).target.apply(lambda s:tuple(sorted(s)))
    assert len(set(sets))==1
print('PASS: 199-month primary dataset, source hashes, foreign keys, unique grain, target/horizon arithmetic, scoring errors, and matched evaluation targets.')

from streamlit.testing.v1 import AppTest
app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
assert not app.exception, str(app.exception)
for page in ['Historical analysis','Economic indicators','Relationship analysis','Model performance','Data explorer','Data architecture','Overview']:
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception, str(app.exception)
    print('PASS page:',page)
app.sidebar.radio[0].set_value('Model performance').run()
app.select_slider[0].set_value(3).run()
app.selectbox[0].set_value('SARIMAX combined').run()
assert not app.exception,str(app.exception)
app.sidebar.radio[0].set_value('Data explorer').run()
next(w for w in app.multiselect if w.label=='Indicators').set_value(['inflation']).run()
assert not app.exception,str(app.exception)
print('PASS: horizon, model, and indicator-selection interactions.')

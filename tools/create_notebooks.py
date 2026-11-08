"""Create the two readable notebook entry points. Training logic lives in notebook cells."""
from pathlib import Path
import json
import textwrap

ROOT = Path(__file__).resolve().parents[1]
def md(s):
    return {'cell_type':'markdown','metadata':{},'source':textwrap.dedent(s).strip().splitlines(True)}
def code(s):
    return {'cell_type':'code','metadata':{},'execution_count':None,'outputs':[], 'source':textwrap.dedent(s).strip().splitlines(True)}
def save(name,cells):
    p=ROOT/'notebooks'/name
    p.parent.mkdir(exist_ok=True)
    if p.exists():
        print('Preserving existing edited notebook:',name)
        return
    p.write_text(json.dumps({'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.12'}},'nbformat':4,'nbformat_minor':5},indent=1),encoding='utf-8')

setup = '''
from pathlib import Path
import sys, json
ROOT = Path.cwd() if (Path.cwd()/'src').exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT))
if sys.prefix == sys.base_prefix and (ROOT/'.packages').exists():
    sys.path.insert(0,str(ROOT/'.packages'))
import pandas as pd
import numpy as np
'''
save('01_data_preparation.ipynb',[
md('''# 01 · Data preparation and audit
Philippine Inflation Observatory. Run this notebook before model development.
The supplied files are treated as source data, not as instructions.
Raw files remain unchanged. See `docs/data-model.md` for the ERD and fact grains.'''),
code(setup),
md('''## Parse source formats
National all-items inflation is already a year-on-year percent. Read monthly average PHP/USD, month-end policy decisions, and DCS M3 levels (million PHP). Revised and provisional M3 date labels are normalized without discarding their original workbook.
The numeric policy parser carries previous rates over five nonnumeric 2011 hold decisions. Review their descriptions below.'''),
code('''from src.prepare import prepare
monthly, manifest = prepare()
display(monthly.head(), monthly.tail())
display(pd.DataFrame(manifest['coverage']).T)
display(pd.read_csv(ROOT/'data/processed/policy_review.csv'))'''),
md('''## Validate grain, continuity and completeness
The wide model table has one national reference month per row. The database stores one indicator × geography × reference month × source vintage per observation. No target or M3 interpolation is allowed.'''),
code('''primary = monthly.loc['2010-01-01':'2026-07-01']
assert len(primary) == 199
assert primary.index.is_unique
assert primary.index.equals(pd.date_range('2010-01-01','2026-07-01',freq='MS',name='date'))
assert primary[['inflation','exchange_rate','m3','policy_rate']].notna().all().all()
assert (primary.m3 > 0).all()
assert np.isclose(monthly.loc['2026-07-01','m3_growth'],100*(monthly.loc['2026-07-01','m3']/monthly.loc['2025-07-01','m3']-1))
print('Passed: 199 continuous primary monthly rows; source series complete.')'''),
md('''## Explore indicators
These plots show association and history, not causal relationships. M3 growth is derived after month alignment. Its first 12 rows are missing because a full prior year is required.'''),
code('''import plotly.express as px
for col in ['inflation','exchange_rate','policy_rate','m3_growth']:
    display(px.line(monthly.reset_index(),x='date',y=col,title=col.replace('_',' ').title()))'''),
md('''## Provenance and research limitations
File SHA-256 values identify uploaded vintages. Original release dates and historical vintages are absent, so availability dates remain unknown. The second notebook uses a conservative delay assumption and reports retrospective evaluation. Unemployment was not supplied. `ms.xls` is retained for reconciliation, not merged as a duplicate M3 series.'''),
code('''display(pd.DataFrame(manifest['files']))
print(chr(10).join(manifest['notes']))''')])

save('02_model_development.ipynb',[
md('''# 02 · Model development and chronological evaluation
All fitting, selection and forecast generation happens in this notebook. The app only reads exported results.
This is a bounded prototype experiment, not a completed statistical study or official forecast.

We compare naive, seasonal naive, two SARIMA specifications, three single-indicator SARIMAX specifications, and one combined SARIMAX. The last 24 months form a final test block; twelve prior months form validation. Candidate selection uses validation only. Every model/horizon is evaluated on the same target months.'''),
code(setup),
code('''import warnings
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tools.sm_exceptions import ConvergenceWarning
monthly = pd.read_csv(ROOT/'data/processed/monthly.csv',parse_dates=['date']).set_index('date').asfreq('MS')
data = monthly.loc[:'2026-07-01'].copy()
OUT = ROOT/'artifacts'
OUT.mkdir(exist_ok=True)
features = ['exchange_rate','policy_rate','m3_growth']
# For target t+h, shift(5) uses predictor t+h-5, no later than origin-2.
X = data[features].shift(5)
start = X.dropna().index[0]
y = data.inflation.loc[start:]
X = X.loc[start:]
assert X.notna().all().all()
test_months = y.index[-24:]
validation_months = y.index[-36:-24]
print('Validation targets:',validation_months[0], 'to', validation_months[-1])
print('Final test targets:',test_months[0], 'to', test_months[-1])'''),
md('''## Fixed candidate specifications and temporal controls
All indicators use a five-month lag relative to target month, allowing three-step forecasts without actual future predictors. Standardization is fitted on each training window only. Future predictor rows are built explicitly from data no later than origin minus two months.
The source data may contain later revisions. These controls do not establish historical publication availability; that needs archived releases.'''),
code('''specs = {
 'Naive': {'family':'naive','features':[]},
 'Seasonal naive': {'family':'seasonal_naive','features':[]},
 'SARIMA A': {'family':'sarima','features':[], 'order':(1,0,0)},
 'SARIMA B': {'family':'sarima','features':[], 'order':(1,1,0)},
 'SARIMAX exchange': {'family':'sarimax','features':['exchange_rate'],'order':(1,0,0)},
 'SARIMAX policy': {'family':'sarimax','features':['policy_rate'],'order':(1,0,0)},
 'SARIMAX M3': {'family':'sarimax','features':['m3_growth'],'order':(1,0,0)},
 'SARIMAX combined': {'family':'sarimax','features':features,'order':(1,0,0)},
}
for spec in specs.values():
    spec.update(seasonal_order=(1,0,0,12),predictor_lag=5)

def predict(name, origin):
    spec = specs[name]
    train = y.loc[:origin]
    dates = pd.date_range(origin+pd.offsets.MonthBegin(1),periods=3,freq='MS')
    if spec['family'] in ['naive','seasonal_naive']:
        values = [train.iloc[-1] if spec['family']=='naive' else train.loc[d-pd.DateOffset(years=1)] for d in dates]
        return np.array(values), None, {'converged':True,'interval':'unavailable for baseline'}
    cols = spec['features']
    xt = xf = None
    if cols:
        xt = X.loc[train.index,cols]
        mean, sd = xt.mean(), xt.std().replace(0,1)
        future = []
        for target in dates:
            source_month = target-pd.DateOffset(months=5)
            assert source_month <= origin-pd.DateOffset(months=2)
            future.append(data.loc[source_month,cols].values)
        xf = (pd.DataFrame(future,index=dates,columns=cols)-mean)/sd
        xt = (xt-mean)/sd
        assert xf.notna().all().all()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always',ConvergenceWarning)
        fit = SARIMAX(train,exog=xt,order=spec['order'],seasonal_order=spec['seasonal_order'],
            trend='c',enforce_stationarity=False,enforce_invertibility=False).fit(disp=False,maxiter=150)
    pred = fit.get_forecast(steps=3,exog=xf)
    residual = fit.resid.iloc[24:]
    diag = {'converged':bool(fit.mle_retvals.get('converged',False)), 'aic':float(fit.aic),
            'residual_mean':float(residual.mean()),
            'ljung_box_p_lag12':float(acorr_ljungbox(residual,lags=[12],return_df=True).lb_pvalue.iloc[0]),
            'warning_count':len(caught)}
    return np.asarray(pred.predicted_mean), np.asarray(pred.conf_int(alpha=.05)), diag

def evaluate(targets,phase):
    rows, runs = [], []
    for name in specs:
        # Cache per origin so overlapping horizons do not refit the same model.
        cache = {}
        for target in targets:
            for h in (1,2,3):
                origin = target-pd.DateOffset(months=h)
                if origin not in cache:
                    try:
                        cache[origin] = predict(name,origin)
                        runs.append({'model':name,'origin':str(origin.date()),'phase':phase,'status':'success',**cache[origin][2]})
                    except Exception as exc:
                        cache[origin] = None
                        runs.append({'model':name,'origin':str(origin.date()),'phase':phase,'status':'failed','error':str(exc)})
                result = cache[origin]
                if result is None:
                    continue
                values, interval, diag = result
                estimate = float(values[h-1])
                rows.append({'model':name,'phase':phase,'origin':str(origin.date()),'target':str(target.date()),
                    'horizon':h,'actual':float(y.loc[target]),'estimate':estimate,
                    'lower_95':None if interval is None else float(interval[h-1,0]),
                    'upper_95':None if interval is None else float(interval[h-1,1]),
                    'error':estimate-float(y.loc[target]),'converged':diag['converged']})
        print(phase,name,'complete',flush=True)
    return pd.DataFrame(rows), runs

def metrics(rows):
    return rows.groupby(['phase','model','horizon']).agg(
        MAE=('error',lambda s:float(s.abs().mean())),
        RMSE=('error',lambda s:float(np.sqrt(np.mean(s**2)))),N=('error','size')).reset_index()'''),
md('''## Validation and model selection
Candidates need all 36 validation forecasts and convergence at every origin to qualify. Lowest mean horizon RMSE wins. Test results never change that selection. This small grid tests candidates; it does not prove predictor causality or stability across regimes.'''),
code('''validation, validation_runs = evaluate(validation_months,'validation')
validation_metrics = metrics(validation)
eligible = []
for name in specs:
    r = validation[validation.model==name]
    if len(r)==36 and r.converged.all() and np.isfinite(r.estimate).all():
        eligible.append(name)
assert eligible, 'No complete converged validation candidate'
scores = validation_metrics[validation_metrics.model.isin(eligible)].groupby('model').RMSE.mean().sort_values()
winner = str(scores.index[0])
display(validation_metrics, scores)
print('Frozen model selection:',winner)'''),
md('''## Untouched final block, evaluated after selection
The specification is frozen. Expanding-window refits may use actual earlier test observations already known at the origin. The final test block is not used to tune the candidate grid or feature choices.'''),
code('''test, test_runs = evaluate(test_months,'test')
all_results = pd.concat([validation,test],ignore_index=True)
all_metrics = metrics(all_results)
display(all_metrics[all_metrics.phase=='test'])
assert all_results.groupby(['phase','model','horizon']).size().eq(all_results.groupby('phase').target.nunique().reindex(all_results.groupby(['phase','model','horizon']).size().index.get_level_values(0)).values).all()
all_results.to_csv(OUT/'backtest.csv',index=False)
all_metrics.to_csv(OUT/'metrics.csv',index=False)
(OUT/'runs.json').write_text(json.dumps(validation_runs+test_runs,indent=2))'''),
md('''## Production refit and export
Refit the selected model through July 2026 and generate August–October forecasts. August actual inflation is separately available for comparison, but was not used to select the model. SARIMA/SARIMAX intervals are conditional model-based 95% intervals and exclude parameter and data-revision uncertainty. Baselines have no interval implementation.'''),
code('''origin = y.index[-1]
values, interval, diagnostics = predict(winner,origin)
assert diagnostics['converged'], 'Selected production fit did not converge'
forecast = pd.DataFrame({'target':pd.date_range(origin+pd.offsets.MonthBegin(1),periods=3,freq='MS'),
    'horizon':[1,2,3],'estimate':values,
    'lower_95':np.nan if interval is None else interval[:,0],
    'upper_95':np.nan if interval is None else interval[:,1]})
forecast.to_csv(OUT/'forecast.csv',index=False)
metadata = {'selected_model':winner,'forecast_origin':str(origin.date()),'training_start':str(y.index[0].date()),
 'validation_start':str(validation_months[0].date()),'validation_end':str(validation_months[-1].date()),
 'test_start':str(test_months[0].date()),'test_end':str(test_months[-1].date()),
 'selection':'Mean validation horizon RMSE; complete converged candidates only',
 'predictor_lag_months':5,'availability':'Retrospective; release dates unavailable; assumes predictors known after two months',
 'eligible_candidates':eligible,'specifications':specs,'production_diagnostics':diagnostics}
(OUT/'model.json').write_text(json.dumps(metadata,indent=2))
display(forecast)
print(json.dumps(diagnostics,indent=2))
from src.store import load_database
load_database()
print('Exported dashboard artifacts and populated normalized database.')''')])
print('Created two notebooks.')

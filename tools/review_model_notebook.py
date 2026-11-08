"""Upgrade existing notebook presentation without changing the candidate grid."""
from pathlib import Path
import json
import textwrap
import uuid

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'notebooks/02_model_development.ipynb'
notebook=json.loads(path.read_text(encoding='utf-8'))
old=notebook['cells']
# Use the original transparent experiment implementation, not app code.
if any('MODEL_REVIEW_VERSION' in ''.join(c['source']) for c in old):
    raise SystemExit('Review notebook already upgraded; edit its cells directly.')
def cell(kind,source):
    item={'cell_type':kind,'id':uuid.uuid4().hex[:8],'metadata':{},'source':textwrap.dedent(source).strip().splitlines(True)}
    if kind=='code': item.update(execution_count=None,outputs=[])
    return item
def md(s): return cell('markdown',s)
def code(s): return cell('code',s)
cells=[]
cells.append(md('''# Philippine inflation forecasting: model review
**Notebook-only progress demonstration.** Run all cells in order with the project's `.venv` Python kernel. Plots, tables, fitted results and interpretations are saved inside this notebook. No web app or database is required.

**Question:** Do lagged exchange rates, the policy rate and M3 growth improve one-, two- and three-month Philippine headline inflation forecasts compared with simple benchmarks and SARIMA?

**Audience:** the student researchers, instructor and evaluators. Intended analytical users include students, researchers and people examining Philippine economic trends. This is an academic estimate, not an official forecast or a causal study.

The supplied midterm rubric asks for dataset understanding, justified preparation, explained algorithms and meaningful comparisons, actual evaluation results, executable evidence, and individual understanding. The sections below provide that evidence; they do not claim a rubric score.

**Review boundary:** retain the existing eight-candidate experiment. Its final 24-month block has already been inspected in an earlier prototype. It is reported honestly as a *previously evaluated holdout*, not a newly untouched test. Do not tune against it in this review. Further tuning needs a new assessment design or newly arriving observations.'''))
cells.append(code('''# MODEL_REVIEW_VERSION = 1
from pathlib import Path
import sys, json, hashlib, warnings
import importlib.metadata as import_metadata
import pandas as pd
import numpy as np
from IPython.display import display, Markdown
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.graphics.gofplots import qqplot
from statsmodels.tools.sm_exceptions import ConvergenceWarning
ROOT=Path.cwd() if (Path.cwd()/'src').exists() else Path.cwd().parent
sys.path.insert(0,str(ROOT))
OUT=ROOT/'artifacts/model_review'
OUT.mkdir(parents=True,exist_ok=True)
get_ipython().run_line_magic('matplotlib','inline')
plt.rcParams.update({'figure.figsize':(11,4),'figure.dpi':110,'savefig.dpi':150,
    'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.18,
    'font.size':10,'axes.titlesize':12,'axes.titleweight':'bold'})
COLORS=['#126a88','#d27c2c','#29815e','#8b61a8']
def show_plot(fig,name):
    fig.tight_layout()
    fig.savefig(OUT/(name+'.png'),bbox_inches='tight')
    plt.show()
    plt.close(fig)
display(pd.DataFrame({'package':['pandas','numpy','statsmodels','matplotlib'],
    'version':[import_metadata.version(p) for p in ['pandas','numpy','statsmodels','matplotlib']]}))
print('Kernel:',sys.executable)
print('Review exports:',OUT)'''))
cells.append(md('''## 1. Source understanding and preparation audit
**Grain:** one national reference month in the analytical table; each underlying observation is one indicator, geography, reference month and supplied-file vintage.

| Series | Source file | Meaning and treatment |
|---|---|---|
| Inflation | two PSA-style CSV exports | National all-items year-on-year percent, both labeled 2018=100; concatenate without recalculating inflation |
| PHP/USD | pesodollar.xlsx | Use monthly average, not end-of-period rate |
| Policy rate | MonetaryPolicyDecisions.xlsx | Extract the first numeric policy-rate clause; last decision per month, then forward-fill known decisions |
| M3 | dcs_srf.xlsx, level row 25 | Million PHP; parse revision/provisional date suffixes, then derive 12-month growth |

The raw files are user-supplied and are not independently authenticated here. Original publication dates and release vintages are absent. Five nonnumeric 2011 hold decisions, exact policy effective dates and the 2016 policy-framework change need manual review. The legacy ms.xls ends in 2005, outside the 2010 onward primary sample. Unemployment was not supplied.

Run notebook 01 if processed inputs do not exist. This notebook then reads them without launching the app or overwriting its artifacts.'''))
cells.append(code('''source_path=ROOT/'data/processed/monthly.csv'
if not source_path.exists():
    from src.prepare import prepare
    prepare()
monthly=pd.read_csv(source_path,parse_dates=['date']).set_index('date').sort_index().asfreq('MS')
manifest=json.loads((ROOT/'data/processed/manifest.json').read_text())
for f in manifest['files']:
    assert hashlib.sha256((ROOT/'data/raw'/f['file']).read_bytes()).hexdigest()==f['sha256']
data=monthly.loc['2010-01-01':'2026-07-01'].copy()
assert len(data)==199 and data.index.is_unique
assert data[['inflation','exchange_rate','policy_rate','m3']].notna().all().all()
expected_growth=data.m3.pct_change(12,fill_method=None)*100
assert np.allclose(data.m3_growth.iloc[12:],expected_growth.iloc[12:])
quality=pd.DataFrame({'unit':['percent YoY','PHP/USD','million PHP','percent','percent YoY'],
    'nonmissing':data.count(),'missing':data.isna().sum(),
    'first':data.apply(lambda s:s.first_valid_index()),'last':data.apply(lambda s:s.last_valid_index())},index=data.columns)
display(quality, data.head(),data.tail())
display(pd.read_csv(ROOT/'data/processed/policy_review.csv'))
print('Passed: source fingerprints, unique monthly grain, 199 primary months and M3-growth reconciliation.')'''))
cells.append(code('''fig,axes=plt.subplots(4,1,figsize=(12,10),sharex=True)
for ax,col,title,color in zip(axes,['inflation','exchange_rate','policy_rate','m3_growth'],
    ['Headline inflation (% YoY)','PHP per US dollar (monthly average)','Policy rate (%)','M3 growth (% YoY)'],COLORS):
    ax.plot(data.index,data[col],color=color,lw=1.6)
    ax.set_ylabel(title)
axes[0].set_title('Primary sample: January 2010 to July 2026')
axes[-1].set_xlabel('Reference month')
show_plot(fig,'01_series_history')
display(Markdown('**Interpretation:** these series have different units and are shown separately. Inflation includes price-pressure episodes and low-inflation periods. Co-movement is not evidence of causality. M3 growth starts only after twelve prior level observations; missing growth is not replaced with zero.'))'''))
setup=''.join(old[2]['source'])
setup=setup[setup.index('features = '):]
cells.append(md('''## 2. Experiment timeline and information availability
All candidates share the same effective sample and target-month blocks. M3 growth loses twelve starting months; the five-month target-relative predictor lag loses five more, so the common model sample starts June 2011.

For origin t and horizon h, use predictor month **t+h-5**. Even at h=3 this is t-2. This assumes predictor values are known within two months, which cannot be verified from the supplied files. Standardization is fitted separately on the training window. No interpolation, backward filling, random splitting or future predictor observations are used.

Origins are labeled by the last inflation reference month used, not a verified historical publication timestamp. Revised data remain a limitation.'''))
cells.append(code(setup+'''
development_end=validation_months[0]-pd.DateOffset(months=3)
development=y.loc[:development_end]
display(pd.DataFrame([
    {'block':'Initial development information','start':y.index[0],'end':development_end,'months':len(development)},
    {'block':'Validation target months','start':validation_months[0],'end':validation_months[-1],'months':len(validation_months)},
    {'block':'Previously evaluated holdout targets','start':test_months[0],'end':test_months[-1],'months':len(test_months)}]))
fig,ax=plt.subplots(figsize=(12,4))
ax.plot(y.index,y,color=COLORS[0],lw=1.6,label='Observed inflation')
ax.axvspan(validation_months[0],validation_months[-1]+pd.offsets.MonthEnd(0),color='#f7d9a0',alpha=.6,label='Validation targets')
ax.axvspan(test_months[0],test_months[-1]+pd.offsets.MonthEnd(0),color='#c9dfee',alpha=.7,label='Holdout targets')
ax.set(title='Chronological target blocks; earlier observations train each origin',ylabel='Inflation (%)',xlabel='Reference month')
ax.legend(loc='upper left',ncol=3)
show_plot(fig,'02_experiment_timeline')
print('At each target, horizon-specific origins precede it by 1, 2 or 3 months. No split is shuffled.')
'''))
cells.append(md('''## 3. Training-only stationarity and lag diagnostics
The following diagnostics use information ending at the earliest validation origin. They describe the development data and do not retune the already evaluated experiment. ADF tests a unit-root null; rejecting that null does not prove model adequacy. Overlapping year-on-year rates can retain serial dependence even when stationary.'''))
cells.append(code('''adf_rows=[]
for label,series in [('Inflation level',development),('First difference',development.diff().dropna())]:
    result=adfuller(series,autolag='AIC')
    adf_rows.append({'series':label,'ADF statistic':result[0],'p value':result[1],'selected lags':result[2],'observations':result[3]})
display(pd.DataFrame(adf_rows).round(5))
fig,axes=plt.subplots(1,2,figsize=(12,4))
plot_acf(development,lags=24,ax=axes[0],zero=False)
plot_pacf(development,lags=24,ax=axes[1],zero=False,method='ywm')
axes[0].set_title('Initial development inflation ACF')
axes[1].set_title('Initial development inflation PACF')
show_plot(fig,'03_development_acf_pacf')
display(Markdown('**Read the plots:** autocorrelation shows persistence across monthly lags. The seasonal period is 12 because observations are monthly. The fixed candidates below test a small AR/seasonal specification and a differenced alternative; this is not an exhaustive order search.'))'''))
cells.append(md('''## 4. Algorithms and fixed experimental settings
**Naive:** repeat the last observed inflation value. **Seasonal naive:** use the same month in the previous year. These are necessary reference points, not placeholder models.

**SARIMA(p,d,q)(P,D,Q,12):** p/q are nonseasonal AR/MA orders; d is differencing. P/D/Q are seasonal counterparts. Candidate A uses (1,0,0)(1,0,0,12); B changes d to 1. **SARIMAX** adds standardized, lagged economic predictors to candidate A. The single-indicator models test incremental information; the combined candidate uses all three.

Statistical fits include an intercept, use up to 150 optimizer iterations, and do not enforce stationarity/invertibility constraints. Convergence is checked; later residual diagnostics must still be assessed. AIC is descriptive, while actual selection uses validation RMSE averaged across the three horizons. Lower training error or a low AIC alone does not select the winner.'''))
functions=''.join(old[4]['source'])
functions=functions.replace('def predict(name, origin):','latest_fit = {}\n\ndef predict(name, origin):')
functions=functions.replace('    pred = fit.get_forecast','    latest_fit[name] = fit\n    pred = fit.get_forecast')
cells.append(code(functions))
cells.append(code('''specification_table=pd.DataFrame([{'model':name,'family':s['family'],
    'order':s.get('order','n/a'),'seasonal order':s['seasonal_order'] if 'order' in s else 'n/a',
    'predictors':', '.join(s['features']) or 'none','predictor lag':5 if s['features'] else 'n/a'} for name,s in specs.items()])
display(specification_table)
print('Forecast error = estimate - actual. Positive error means overprediction.')'''))
cells.append(md('''## 5. Expanding-origin validation and frozen selection
Each model produces 36 validation forecasts: twelve common target months at each of three horizons. The training window expands only through its origin. A candidate must supply all forecasts, finite values and convergence at every origin to qualify. Failures are exposed rather than replaced with a favorable fallback.'''))
cells.append(code(''.join(old[6]['source'])))
cells.append(code('''validation_audit=pd.DataFrame(validation_runs)
display(validation_audit.groupby('model').agg(runs=('status','size'),
    failed=('status',lambda s:int(s.ne('success').sum())),
    converged=('converged',lambda s:int(s.fillna(False).sum()))))
fig,axes=plt.subplots(1,2,figsize=(13,5))
scores.sort_values().plot.barh(ax=axes[0],color=COLORS[0])
axes[0].invert_yaxis()
axes[0].set(title='Eligible validation ranking',xlabel='Mean horizon RMSE (pp)',ylabel='')
validation_metrics.pivot(index='model',columns='horizon',values='RMSE').reindex(scores.index).plot.bar(ax=axes[1],color=COLORS[:3])
axes[1].set(title='Validation error by horizon',ylabel='RMSE (pp)',xlabel='')
axes[1].tick_params(axis='x',labelrotation=65)
axes[1].legend(title='Horizon (months)')
show_plot(fig,'04_validation_comparison')
display(Markdown(f'**Selection:** {winner} has the lowest mean validation-horizon RMSE among complete converged candidates ({scores.iloc[0]:.3f} pp). The winner is fixed before reporting holdout results.'))'''))
cells.append(md('''## 6. Previously evaluated holdout: actual experimental results
The original specification is frozen. Earlier holdout observations may enter later expanding fits only after their origin has arrived. No new model, feature or order is chosen using this block. Because this block has been inspected before, do not label this run a fresh untouched test.'''))
test_code=''.join(old[8]['source'])
test_code=test_code.replace("assert all_results.groupby(['phase','model','horizon']).size().eq(all_results.groupby('phase').target.nunique().reindex(all_results.groupby(['phase','model','horizon']).size().index.get_level_values(0)).values).all()",'''for phase,expected in [('validation',12),('test',24)]:
    expected_grid=pd.MultiIndex.from_product([[phase],list(specs),[1,2,3]],names=['phase','model','horizon'])
    counts=all_results.groupby(['phase','model','horizon']).size().reindex(expected_grid,fill_value=0)
    assert counts.eq(expected).all(), counts[counts.ne(expected)].to_dict()
    sets=all_results[all_results.phase==phase].groupby(['model','horizon']).target.apply(lambda v:tuple(sorted(v)))
    assert len(set(sets))==1, 'Unmatched target months across competitors'
display(pd.DataFrame(test_runs).groupby('model').agg(runs=('status','size'),converged=('converged','sum')))''')
cells.append(code(test_code))
cells.append(code('''test_metrics=all_metrics[all_metrics.phase=='test']
fig,axes=plt.subplots(1,2,figsize=(14,5))
for ax,metric in zip(axes,['MAE','RMSE']):
    test_metrics.pivot(index='model',columns='horizon',values=metric).plot.bar(ax=ax,color=COLORS[:3])
    ax.set(title=f'Previously evaluated holdout: {metric}',ylabel=f'{metric} (percentage points)',xlabel='')
    ax.tick_params(axis='x',labelrotation=65)
    ax.legend(title='Horizon (months)')
show_plot(fig,'05_holdout_model_comparison')
selected_test=test[test.model==winner].copy()
comparison=test_metrics[test_metrics.model.isin([winner,'Naive','SARIMA A'])].pivot(index='horizon',columns='model',values='RMSE')
comparison['RMSE reduction vs naive (%)']=100*(comparison['Naive']-comparison[winner])/comparison['Naive']
display(comparison.round(4))
display(Markdown('**Interpretation:** MAE is average absolute error in percentage points. RMSE gives greater weight to large misses. Compare models only on matching targets and horizons. Improvement in this supplied vintage is not proof of causal influence or guaranteed future performance.'))'''))
cells.append(code('''fig,axes=plt.subplots(3,1,figsize=(12,10),sharex=True)
for h,ax in zip([1,2,3],axes):
    rows=selected_test[selected_test.horizon==h].sort_values('target')
    dates=pd.to_datetime(rows.target)
    ax.plot(dates,rows.actual,label='Observed inflation',color=COLORS[0],lw=2)
    ax.plot(dates,rows.estimate,label=f'{h}-month forecast',color=COLORS[1],ls='--',marker='o',ms=3)
    if rows.lower_95.notna().all():
        ax.fill_between(dates,rows.lower_95,rows.upper_95,color=COLORS[1],alpha=.14,label='Conditional 95% interval')
    ax.set(title=f'{winner}: {h}-month-ahead holdout forecasts',ylabel='Inflation (%)')
    ax.legend(loc='upper left',ncol=3)
axes[-1].set_xlabel('Target month')
show_plot(fig,'06_actual_vs_predicted')
display(selected_test[['origin','target','horizon','actual','estimate','error']].tail(12).round(4))
display(Markdown('**Read the plot:** forecast misses can increase around rapid changes in inflation. The forecast line was generated from an earlier origin for each horizon, not fitted using the displayed target value. Conditional intervals do not include all parameter or data-revision uncertainty.'))'''))
cells.append(code('''error_summary=selected_test.groupby('horizon').agg(
    N=('error','size'),bias=('error','mean'),MAE=('error',lambda s:s.abs().mean()),
    RMSE=('error',lambda s:np.sqrt(np.mean(s**2))),converged_forecasts=('converged','sum'))
selected_test['covered_95']=(selected_test.actual>=selected_test.lower_95)&(selected_test.actual<=selected_test.upper_95)
if selected_test.lower_95.notna().all():
    error_summary['conditional_interval_coverage']=selected_test.groupby('horizon').covered_95.mean()
display(error_summary.round(4))
fig,axes=plt.subplots(1,2,figsize=(12,4))
for h,color in zip([1,2,3],COLORS):
    rows=selected_test[selected_test.horizon==h].sort_values('target')
    axes[0].plot(pd.to_datetime(rows.target),rows.error,label=f'h={h}',color=color)
axes[0].axhline(0,color='black',lw=.8)
axes[0].set(title='Holdout forecast errors',ylabel='Estimate minus actual (pp)',xlabel='Target month')
axes[0].legend()
axes[1].boxplot([selected_test.loc[selected_test.horizon==h,'error'] for h in [1,2,3]],tick_labels=['1 month','2 months','3 months'])
axes[1].axhline(0,color='black',lw=.8)
axes[1].set(title='Error distributions by horizon',ylabel='Error (pp)')
show_plot(fig,'07_forecast_errors')
display(Markdown('**Interpretation:** positive bias indicates average overprediction; negative bias indicates underprediction. Coverage is an empirical descriptive fraction from only 24 targets per horizon. Forecast errors overlap across horizons and origins, so these observations are not independent trials.'))'''))
cells.append(md('''## 7. Selected-model refit and three-month forecast
Refit the frozen validation winner using inflation through July 2026. Generate August-October 2026 estimates and conditional 95% intervals. August's supplied actual is available only for an explicitly separated later comparison. There are no invented actuals for later months.'''))
final=''.join(old[10]['source'])
final=final[:final.index('from src.store import load_database')]
final=final.replace('display(forecast)','review_fit=latest_fit.get(winner)\ndisplay(forecast.round(4))')
cells.append(code(final))
cells.append(code('''fig,ax=plt.subplots(figsize=(12,5))
history=y.iloc[-36:]
ax.plot(history.index,history,label='Observed through origin',color=COLORS[0],lw=2)
ax.plot([origin,*forecast.target],[y.iloc[-1],*forecast.estimate],label='Frozen-model forecast',color=COLORS[1],ls='--',marker='o')
if forecast.lower_95.notna().all():
    ax.fill_between(forecast.target,forecast.lower_95,forecast.upper_95,color=COLORS[1],alpha=.18,label='Conditional 95% interval')
later=monthly.loc[monthly.index>origin,'inflation'].dropna().reindex(forecast.target).dropna()
ax.scatter(later.index,later.values,label='Later supplied actual (not training)',color='#6d3791',s=65,zorder=5)
ax.axvline(origin,color='grey',ls=':',lw=1)
ax.set(title=f'July 2026 origin: {winner}',ylabel='Headline inflation (%)',xlabel='Reference / target month')
ax.legend(loc='upper left',ncol=2)
show_plot(fig,'08_three_month_forecast')
display(pd.DataFrame({'forecast':forecast.set_index('target').estimate,'later_supplied_actual':later}))
display(Markdown(f'**Forecast interpretation:** from the origin value of {y.iloc[-1]:.1f}%, the model estimates '+', '.join(f'{r.estimate:.2f}% for {r.target:%B %Y}' for r in forecast.itertuples())+'. These are provisional analytical estimates; residual diagnostics below determine whether the specification is adequate.'))'''))
cells.append(md('''## 8. Model adequacy: coefficients, residuals and autocorrelation
Optimizer convergence only means the fitting routine stopped successfully. It does not mean errors are white noise or the specification is reliable. Coefficients on standardized lagged predictors are conditional associations, not causal effects or a separate feature-importance ranking.

For residual review, discard at least 24 starting observations and the model's likelihood burn-in. Ljung-Box p-values below use an AR/MA degrees-of-freedom adjustment (p+q+P+Q). They are descriptive checks on a refit after selection, not extra holdout evidence.'''))
cells.append(code('''if review_fit is None:
    display(Markdown('The selected baseline has no fitted SARIMA residual or coefficient diagnostics.'))
else:
    display(review_fit.summary())
    bounds=review_fit.conf_int()
    coefficient_table=pd.DataFrame({'coefficient':review_fit.params,'std_error':review_fit.bse,'p_value':review_fit.pvalues,
        'lower_95':bounds.iloc[:,0],'upper_95':bounds.iloc[:,1]})
    display(coefficient_table.round(5))
    coefficient_table.to_csv(OUT/'selected_coefficients.csv')
    burn=max(24,int(review_fit.loglikelihood_burn))
    residual=review_fit.resid.iloc[burn:].dropna()
    specification=specs[winner]
    model_df=sum([specification['order'][0],specification['order'][2],specification['seasonal_order'][0],specification['seasonal_order'][2]])
    lb=acorr_ljungbox(residual,lags=[6,12,18,24],model_df=model_df,return_df=True)
    display(lb)
    lb.to_csv(OUT/'ljung_box.csv')
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    axes[0,0].plot(residual.index,residual,color=COLORS[0],lw=1)
    axes[0,0].axhline(0,color='black',lw=.7)
    axes[0,0].set(title='Refit residuals after burn-in',ylabel='Residual (pp)')
    axes[0,1].hist(residual,bins=18,color=COLORS[0],alpha=.8)
    axes[0,1].set(title='Residual distribution',xlabel='Residual (pp)',ylabel='Count')
    plot_acf(residual,lags=24,zero=False,ax=axes[1,0])
    axes[1,0].set_title('Residual ACF')
    qqplot(residual,line='s',ax=axes[1,1])
    axes[1,1].set_title('Residual normal Q-Q plot')
    show_plot(fig,'09_residual_diagnostics')
    adequate=bool(lb.lb_pvalue.gt(.05).all())
    display(Markdown('**Adequacy review:** '+('No listed Ljung-Box check rejects the no-autocorrelation null at 5%; this is not proof of adequacy.' if adequate else 'Residual autocorrelation remains at one or more inspected lags. Treat the selected model as provisional: it wins this validation comparison but does not pass full residual adequacy review.')))
    print('Adjusted Ljung-Box model_df:',model_df,'; residual burn-in:',burn)'''))
cells.append(md('''## 9. Future-information perturbation check
At one historical origin, replace later inflation and predictor records with extreme values, then recompute the same forecast. It must be unchanged. Restore the original data immediately. This tests the implemented information boundary; it does not authenticate publication dates or remove historical revisions.'''))
cells.append(code('''audit_origin=test_months[0]-pd.DateOffset(months=3)
before=predict(winner,audit_origin)[0]
saved_data,saved_y,saved_X=data.copy(deep=True),y.copy(deep=True),X.copy(deep=True)
try:
    data.loc[data.index>audit_origin,:]=1e6
    y.loc[y.index>audit_origin]=1e6
    X.loc[X.index>audit_origin,:]=1e6
    after=predict(winner,audit_origin)[0]
    assert np.allclose(before,after,atol=1e-7,rtol=1e-7), 'Future-information leakage detected'
finally:
    data,y,X=saved_data,saved_y,saved_X
display(pd.DataFrame({'horizon':[1,2,3],'before_future_perturbation':before,'after_future_perturbation':after,'difference':after-before}))
print('PASS: later input changes did not alter forecasts at the historical origin.')'''))
cells.append(md('''## 10. Review conclusion and demonstration discussion
**What is implemented:** a reproducible monthly dataset audit; eight explained benchmarks/statistical candidates; expanding-origin validation at three horizons; frozen validation selection; per-horizon holdout metrics and plots; a three-month forecast; fitted-model/residual diagnostics; and a future-input invariance check.

**What is not established:** official data authentication, true real-time publication availability, robustness across historical vintages, causal economic effects, broad predictor stability, or deployment readiness. Residual adequacy must be assessed separately from convergence and validation rank.

**Suggested oral walkthrough:**
1. Explain the target, units, source files, monthly grain and 199-month primary sample.
2. Explain missing markers, M3 growth, policy carry-forward and the common effective model sample.
3. Demonstrate the origin/target/lag rule with one horizon; explain why there is no random split.
4. Explain SARIMA orders, SARIMAX predictors, naive benchmarks and validation-only selection.
5. Read actual plotted errors and MAE/RMSE values in percentage points, then discuss residual weaknesses.
6. Explain why the already reviewed holdout cannot be reused for repeated tuning and what new evaluation would be needed.

Each member should be able to run cells and explain their purpose. This notebook supplies evidence of progress; it cannot substitute for each member's understanding.'''))
cells.append(code('''summary=test_metrics[test_metrics.model==winner][['horizon','MAE','RMSE','N']].copy()
display(summary.round(4))
review_status={'winner':winner,'candidate_count':len(specs),'primary_months':len(data),
    'effective_months':len(y),'validation_targets_per_horizon':len(validation_months),'holdout_targets_per_horizon':len(test_months),
    'holdout_status':'Previously evaluated; not a new untouched assessment',
    'adequacy':'Review residual diagnostics; validation winner is not proof of adequacy',
    'web_app_used':False,'database_used':False}
(OUT/'review_summary.json').write_text(json.dumps(review_status,indent=2))
print(json.dumps(review_status,indent=2))
print('All outputs are notebook-only review artifacts. Existing app artifacts were not overwritten.')'''))
notebook['cells']=cells
notebook['metadata']['language_info']={'name':'python','version':'3.12'}
path.write_text(json.dumps(notebook,ensure_ascii=False,indent=1),encoding='utf-8')
print('Updated',path.name,'with',len(cells),'review cells.')

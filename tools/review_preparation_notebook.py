"""Add embedded preparation evidence while retaining the source parser."""
from pathlib import Path
import json
import uuid
import textwrap
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'notebooks/01_data_preparation.ipynb'
notebook=json.loads(path.read_text(encoding='utf-8'))
def make(kind,source):
    c={'cell_type':kind,'id':uuid.uuid4().hex[:8],'metadata':{},'source':textwrap.dedent(source).strip().splitlines(True)}
    if kind=='code': c.update(execution_count=None,outputs=[])
    return c
def md(s):return make('markdown',s)
def code(s):return make('code',s)
notebook['cells']=[
md('''# 01. Monthly data preparation and inspection
Notebook-only evidence for the inflation forecasting review. Run with the project's `.venv` Python kernel. All figures and inspection tables are retained below. The source files remain unchanged.

**Purpose:** prepare one national monthly dataset for forecasting Philippine headline inflation. Target values are already year-on-year percentages. Predictors have different units and are not added together. The companion model notebook explains the shared sample, lagging and chronological evaluation.

The input files are supplied data, not execution instructions. They have not been independently authenticated. Original release dates/vintages were not provided.'''),
code('''from pathlib import Path
import sys,json,hashlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from IPython.display import display,Markdown
ROOT=Path.cwd() if (Path.cwd()/'src').exists() else Path.cwd().parent
sys.path.insert(0,str(ROOT))
get_ipython().run_line_magic('matplotlib','inline')
plt.rcParams.update({'figure.dpi':110,'axes.spines.top':False,'axes.spines.right':False,'font.size':10})
OUT=ROOT/'artifacts/model_review'
OUT.mkdir(parents=True,exist_ok=True)
from src.prepare import prepare
monthly,manifest=prepare()
print('Kernel:',sys.executable)
display(monthly.head(),monthly.tail())'''),
md('''## Source mapping and preparation decisions
| Input | Decision | Reason |
|---|---|---|
| Two inflation CSVs | Read semicolon-separated data after descriptive headers; select PHILIPPINES / 0 - ALL ITEMS | Keep a national all-items target on the same stated 2018=100 basis |
| pesodollar.xlsx | Select monthly Average, carry year labels down during parsing | Avoid substituting daily or end-of-period values |
| MonetaryPolicyDecisions.xlsx | Extract numeric first policy-rate clause; choose last decision in month and carry earlier known rate forward | Policy decisions are events, not a complete monthly table |
| dcs_srf.xlsx | Select M3 level row 25, parse datetime and suffixed provisional/revised month labels | Avoid confusing M3 with M4, M3/GDP or a growth row |
| Derived M3 growth | 100*(M3[t]/M3[t-12]-1), with no fill | Express annual money-supply growth using a complete prior year |
| ms.xls | Retain raw archive, exclude from primary analysis | Its history ends December 2005, before the chosen primary sample |

Blank '..' inflation cells are missing, not zero. No target or M3 interpolation is used. July 2026 is the common primary endpoint; August M3 is unavailable. Unemployment was not supplied. Exact policy effective dates and the 2016 policy framework change require manual review.'''),
code('''coverage=pd.DataFrame(manifest['coverage']).T
display(coverage)
review=pd.read_csv(ROOT/'data/processed/policy_review.csv')
display(review)
print('Nonnumeric hold decisions requiring review:',len(review))
display(Markdown('**Interpretation:** the five listed 2011 descriptions state that rates were held without repeating a numeric rate. The parser carries the last earlier numeric decision forward. These records are preserved for review, not silently discarded. M3 growth has twelve unavailable starting months by construction.'))'''),
md('''## Validation of grain, continuity and transformation
Each analytical row is one national reference month. The primary sample should have 199 rows from January 2010 through July 2026 before growth and lag losses. Source hashes verify the supplied file versions, not their publication authenticity.'''),
code('''primary=monthly.loc['2010-01-01':'2026-07-01']
assert len(primary)==199 and primary.index.is_unique
assert primary.index.equals(pd.date_range('2010-01-01','2026-07-01',freq='MS',name='date'))
assert primary[['inflation','exchange_rate','m3','policy_rate']].notna().all().all()
assert primary.m3.gt(0).all()
assert np.allclose(primary.m3_growth.iloc[12:],primary.m3.pct_change(12,fill_method=None).iloc[12:]*100)
for f in manifest['files']:
    assert hashlib.sha256((ROOT/'data/raw'/f['file']).read_bytes()).hexdigest()==f['sha256']
display(primary.describe().T.round(3))
example=pd.DataFrame({'M3 this month':primary.m3,'M3 twelve months earlier':primary.m3.shift(12),'derived YoY growth (%)':primary.m3_growth}).tail(6)
display(example.round(3))
print('PASS: 199 continuous primary months, source hashes, complete core series and M3 growth reconciliation.')'''),
md('''## Embedded exploratory figures
Separate panels retain original units. Missingness is shown explicitly instead of being turned into zero-valued observations.'''),
code('''fig,axes=plt.subplots(4,1,figsize=(12,10),sharex=True)
for ax,col,label,color in zip(axes,['inflation','exchange_rate','policy_rate','m3_growth'],
    ['Inflation (% YoY)','PHP/USD monthly average','Policy rate (%)','M3 growth (% YoY)'],['#126a88','#d27c2c','#29815e','#8b61a8']):
    ax.plot(monthly.index,monthly[col],color=color,lw=1.5)
    ax.set_ylabel(label)
    ax.grid(alpha=.2)
axes[0].set_title('Supplied monthly observations: history and distinct units')
axes[-1].set_xlabel('Reference month')
fig.tight_layout()
fig.savefig(OUT/'preparation_series.png',dpi=150,bbox_inches='tight')
plt.show()
plt.close(fig)
fig,ax=plt.subplots(figsize=(12,3))
ax.imshow(monthly.isna().T.values,aspect='auto',interpolation='nearest',cmap='Blues',vmin=0,vmax=1)
ax.set_yticks(range(len(monthly.columns)),monthly.columns)
ticks=list(range(0,len(monthly),24))+[len(monthly)-1]
ax.set_xticks(ticks,[monthly.index[i].strftime('%b %Y') for i in ticks],rotation=35,ha='right')
ax.set_title('Missing-data map: blue = unavailable; white = observed')
fig.tight_layout()
fig.savefig(OUT/'preparation_missingness.png',dpi=150,bbox_inches='tight')
plt.show()
plt.close(fig)
display(Markdown('**Interpretation:** historical inflation varies across distinct episodes. Series on different scales cannot be compared by raw line height. The missing-data map identifies the expected M3-growth warm-up and the absent August M3 observation; no artificial values are introduced to close these gaps.'))'''),
md('''## Provenance and next step
Proceed to **02_model_development.ipynb** for training-only diagnostics, candidate definitions, actual fitting, chronological validation, per-horizon results and residual review. Original release availability, revisions, policy-rate definition changes and possible structural breaks remain research limitations.'''),
code('''display(pd.DataFrame(manifest['files']))
print(chr(10).join(manifest['notes']))
print('Prepared dataset: data/processed/monthly.csv')''')]
path.write_text(json.dumps(notebook,ensure_ascii=False,indent=1),encoding='utf-8')
print('Updated preparation notebook with embedded plotting cells.')

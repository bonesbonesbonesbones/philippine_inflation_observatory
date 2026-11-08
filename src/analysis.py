"""Descriptive analysis only; model fitting remains in the notebooks."""
import numpy as np
import pandas as pd

LABELS={'inflation':'Headline inflation','exchange_rate':'PHP/USD exchange rate','policy_rate':'BSP policy rate','m3':'M3 money supply','m3_growth':'M3 year-on-year growth'}
UNITS={'inflation':'%','exchange_rate':'PHP/USD','policy_rate':'%','m3':'million PHP','m3_growth':'%'}

def history_narrative(frame):
    s=frame.inflation.dropna().sort_index()
    if s.empty:
        return 'No inflation observations match the selected historical filters.'
    if len(s)==1:
        return f'The selected period contains one observation: {s.iloc[0]:.1f}% in {s.index[0]:%B %Y}. Select more months to describe a trend.'
    delta=s.iloc[-1]-s.iloc[0]
    direction='rose' if delta>0 else 'fell' if delta<0 else 'was unchanged'
    return (f'Across {len(s)} selected months, headline inflation {direction} from {s.iloc[0]:.1f}% '
            f'in {s.index[0]:%B %Y} to {s.iloc[-1]:.1f}% in {s.index[-1]:%B %Y} '
            f'({delta:+.2f} percentage points). The unweighted average monthly year-on-year rate was {s.mean():.2f}%. '
            f'The highest selected rate was {s.max():.1f}% in {s.idxmax():%B %Y}; '
            f'the lowest was {s.min():.1f}% in {s.idxmin():%B %Y}. '
            'These are summaries of the selected observations, not cumulative inflation or an official annual rate.')

def relationship_pairs(full,targets,indicator,lag=0,changes=False):
    values=full[['inflation',indicator]].copy().sort_index().asfreq('MS')
    if changes:
        values=values.diff()
    # Shift on complete calendar before filtering: lag is in calendar months.
    pairs=pd.DataFrame({'inflation':values.inflation,'indicator':values[indicator].shift(lag)},index=values.index)
    pairs['source_month']=pairs.index-pd.DateOffset(months=lag)
    return pairs.loc[pairs.index.isin(targets)].dropna()

def correlation(pairs,method='pearson'):
    if len(pairs)<3 or pairs.inflation.nunique()<2 or pairs.indicator.nunique()<2:
        return None
    result=pairs.inflation.corr(pairs.indicator,method=method)
    return float(result) if np.isfinite(result) else None

def relationship_narrative(pairs,indicator,lag,method,changes):
    r=correlation(pairs,method)
    if r is None:
        return 'A relationship cannot be estimated for this selection: at least three paired months and variation in both series are required. Widen the history window or select another indicator.'
    direction='positive' if r>0 else 'negative' if r<0 else 'zero'
    subject='monthly changes' if changes else 'observed levels'
    timing='in the same month' if lag==0 else f'{lag} calendar month(s) earlier'
    movement=('Higher indicator values tended to accompany higher inflation values.' if r>0 else
              'Higher indicator values tended to accompany lower inflation values.' if r<0 else
              'No directional association is visible in this correlation.')
    return (f'For {len(pairs)} complete paired months, {method.title()} correlation between inflation {subject} '
            f'and {LABELS[indicator]} {subject} {timing} is {r:+.3f}. '
            f'The association is {direction}. {movement} '
            'It does not show that the indicator causes inflation or improves a forecast. '
            'Time trends, autocorrelation, revisions and other factors can affect the result. '
            'This exploratory view does not change the notebook-selected model.')

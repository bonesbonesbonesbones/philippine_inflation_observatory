from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
import numpy as np
from src.analysis import relationship_pairs,correlation,history_narrative
from src.filters import resolve_window,shift_window

# A selected target in March must pair with January for lag 2, even when
# January is outside the displayed target window. Missing calendar months
# must not be treated as adjacent observations.
idx=pd.date_range('2020-01-01',periods=6,freq='MS')
df=pd.DataFrame({'inflation':range(6),'exchange_rate':np.arange(6)*2.0},index=idx)
pairs=relationship_pairs(df,idx[2:],'exchange_rate',2)
assert pairs.iloc[0].indicator==0 and pairs.iloc[0].source_month==idx[0]
assert correlation(pairs)==1
gapped=df.drop(idx[1])
pairs=relationship_pairs(gapped,idx[2:],'exchange_rate',1)
assert idx[2] not in pairs.index
assert correlation(pd.DataFrame({'inflation':[1,1,1],'indicator':[1,2,3]})) is None
assert correlation(pd.DataFrame({'inflation':[1,2],'indicator':[1,2]})) is None
assert 'one observation' in history_narrative(df.iloc[:1])
assert 'No inflation' in history_narrative(df.iloc[:0])
print('PASS: calendar-lag alignment, missing-month gaps, constant/short samples and narrative boundaries.')
calendar=pd.date_range('2010-01-01','2026-08-01',freq='MS')
assert len(resolve_window(calendar,'Last 12 months'))==12
assert len(resolve_window(calendar,'Last 3 years'))==36
assert len(resolve_window(calendar,'Latest year'))==8
assert len(resolve_window(calendar,'Choose years',[2020,2022]))==24
assert len(resolve_window(calendar,'Choose years',[]))==0
assert len(resolve_window(calendar,'Custom range',custom=('2020-02-15','2020-04-29')))==3
assert shift_window(calendar,calendar[0],calendar[11],-1)==(calendar[0],calendar[11])
assert shift_window(calendar,calendar[-12],calendar[-1],-1)==(calendar[-24],calendar[-13])

from streamlit.testing.v1 import AppTest
app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
assert not app.exception,str(app.exception)
assert app.metric[1].label=='Average monthly rate'
initial_average=app.metric[1].value
app.get('button_group')[0].set_value('Last 12 months').run()
assert not app.exception,str(app.exception)
assert app.metric[1].value!=initial_average
assert app.button(key='history_next').disabled
app.button(key='history_previous').click().run()
assert not app.exception,str(app.exception)
assert app.get('button_group')[0].value=='Custom range'
assert len(app.select_slider[0].value)==2
assert not app.button(key='history_next').disabled
# The visible date fields and slider resolve to exactly the same months.
assert tuple(pd.Timestamp(d) for d in app.date_input[0].value)==tuple(app.select_slider[0].value)
app.date_input[0].set_value((pd.Timestamp('2020-02-15').date(),pd.Timestamp('2020-04-29').date())).run()
assert not app.exception,str(app.exception)
assert app.select_slider[0].value==(pd.Timestamp('2020-02-01'),pd.Timestamp('2020-04-01'))
app.select_slider[0].set_value((pd.Timestamp('2021-01-01'),pd.Timestamp('2021-12-01'))).run()
assert not app.exception,str(app.exception)
assert app.date_input[0].value==(pd.Timestamp('2021-01-01').date(),pd.Timestamp('2021-12-01').date())
app.date_input[0].set_value((pd.Timestamp('2020-03-01').date(),)).run()
assert not app.exception,str(app.exception)
assert any('last complete selection' in w.value for w in app.info)
assert app.select_slider[0].value==(pd.Timestamp('2021-01-01'),pd.Timestamp('2021-12-01'))
app.get('button_group')[0].set_value('Choose years').run()
next(w for w in app.multiselect if w.label=='Which years would you like to compare?').set_value([2020]).run()
app.sidebar.radio[0].set_value('Relationship analysis').run()
assert not app.exception,str(app.exception)
next(w for w in app.selectbox if w.label=='Analyze').set_value('Levels').run()
next(w for w in app.selectbox if w.label=='Correlation method').set_value('spearman').run()
next(w for w in app.number_input if w.label=='Indicator lag (months)').set_value(5).run()
assert not app.exception,str(app.exception)
assert app.metric[0].value=='12'
app.sidebar.radio[0].set_value('Historical analysis').run()
assert not app.exception,str(app.exception)
# Filter values carry into another view. Inflation rates are summarized, never summed.
assert app.metric[0].value=='12'
app.sidebar.radio[0].set_value('Model performance').run()
assert not app.exception,str(app.exception)
app.sidebar.radio[0].set_value('Historical analysis').run()
assert app.metric[0].value=='12'
next(w for w in app.multiselect if w.label=='Which years would you like to compare?').set_value([]).run()
assert not app.exception,str(app.exception)
assert any('Select at least one year' in x.value for x in app.info)
app.button(key='history_reset').click().run()
assert not app.exception,str(app.exception)
assert app.metric[0].value=='200'
print('PASS: reactive KPIs, quick periods, stepping, date/slider synchronization, persistent year filters, empty selection and reset.')

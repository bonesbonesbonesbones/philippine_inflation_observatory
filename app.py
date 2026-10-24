from pathlib import Path
import json
import sqlite3
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title='Inflation Observatory',page_icon='◉',layout='wide')
st.markdown('''<style>
.stApp {background:#f5f7fb;color:#13273a}
.block-container {padding-top:4.2rem;max-width:1450px}
h1,h2,h3 {letter-spacing:-.035em;color:#112c3c}
[data-testid="stSidebar"] {background:#102d3a;color:#e2edf1}
[data-testid="stSidebar"] * {color:#e2edf1}
[data-testid="stMetric"] {background:white;border:1px solid #e0e8ed;border-radius:14px;padding:20px}
[data-testid="stMetricLabel"] {color:#647787}
[data-testid="stMetricValue"] {font-size:1.55rem;color:#0b726b}
[data-testid="stColumn"] {min-width:0}
[data-testid="stMetricValue"] > div {white-space:normal;overflow-wrap:anywhere;max-width:100%;text-overflow:clip;line-height:1.3}
[data-testid="stMetricLabel"] p {white-space:normal;overflow-wrap:anywhere;text-overflow:clip;line-height:1.5}
.eyebrow {color:#098078;font-size:12px;letter-spacing:.17em;font-weight:700;margin-bottom:12px}
.subtitle {color:#647787;font-size:16px;max-width:800px;margin-bottom:28px}
.note {background:#e8f2f2;border-left:3px solid #128980;padding:14px 18px;border-radius:6px;color:#315c63;font-size:14px;margin:16px 0}
</style>''',unsafe_allow_html=True)

st.sidebar.markdown('## ◉ INFLATION\nOBSERVATORY')
st.sidebar.caption('PHILIPPINES / RESEARCH PROTOTYPE')
st.sidebar.divider()
page=st.sidebar.radio('Workspace',['Overview','Economic indicators','Model performance','Data explorer','Data architecture'],label_visibility='collapsed')
st.sidebar.divider()
st.sidebar.markdown('**Monthly national headline inflation**')
st.sidebar.caption('PSA and BSP source files supplied for the project. Experimental analytical estimates, not official government forecasts.')

if not (ROOT/'artifacts/model.json').exists():
    st.title('Inflation Observatory')
    st.info('Run notebooks 01 and 02 to prepare data and generate forecast artifacts.')
    st.stop()

@st.cache_data
def load_data(version):
    with sqlite3.connect(ROOT/'database/inflation.db') as db:
        rows=pd.read_sql_query('''SELECT o.reference_month,i.code,o.value FROM observation o
            JOIN indicator i ON i.indicator_id=o.indicator_id
            JOIN snapshot_observation so ON so.observation_id=o.observation_id
            WHERE so.snapshot_id=(SELECT snapshot_id FROM dataset_snapshot ORDER BY created_at DESC LIMIT 1)''',db)
    df=rows.pivot(index='reference_month',columns='code',values='value')
    df.index=pd.to_datetime(df.index)
    df.index.name='date'
    df['m3_growth']=df.m3.pct_change(12,fill_method=None)*100
    return df

data=load_data((ROOT/'database/inflation.db').stat().st_mtime_ns)
meta=json.loads((ROOT/'artifacts/model.json').read_text())
manifest=json.loads((ROOT/'data/processed/manifest.json').read_text())
forecast=pd.read_csv(ROOT/'artifacts/forecast.csv',parse_dates=['target'])
backtest=pd.read_csv(ROOT/'artifacts/backtest.csv',parse_dates=['origin','target'])
metrics=pd.read_csv(ROOT/'artifacts/metrics.csv')
origin=pd.Timestamp(meta['forecast_origin'])

def heading(title,subtitle):
    st.markdown('<div class="eyebrow">PHILIPPINE ECONOMIC INTELLIGENCE</div>',unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<div class="subtitle">{subtitle}</div>',unsafe_allow_html=True)

def style(fig,title=None,height=390):
    has_legend=any(trace.name and trace.showlegend is not False for trace in fig.data)
    fig.update_layout(template='plotly_white',height=height,
        title=dict(text=title,x=.02,y=.98,xanchor='left',yanchor='top',font=dict(size=16),automargin=True),
        paper_bgcolor='white',plot_bgcolor='white',margin=dict(l=24,r=24,t=74,b=120 if has_legend else 55,autoexpand=True),
        font=dict(family='Segoe UI, sans-serif',color='#425a6b'),
        legend=dict(orientation='h',y=-.24,x=0,yanchor='top',xanchor='left',
            entrywidth=180,entrywidthmode='pixels',font=dict(size=11)),hovermode='x unified')
    fig.update_xaxes(showgrid=False,automargin=True,title_standoff=18)
    fig.update_yaxes(gridcolor='#edf1f5',zeroline=False,automargin=True,title_standoff=16)
    return fig

if page=='Overview':
    heading('A clearer view of inflation','Explore the historical record and a transparent, one-to-three-month outlook for Philippine headline inflation.')
    latest=data.inflation.dropna()
    c=st.columns(4)
    c[0].metric('Latest observation',f'{latest.iloc[-1]:.1f}%',f'{latest.iloc[-1]-latest.iloc[-2]:+.1f} pp',delta_color='off')
    c[0].caption(latest.index[-1].strftime('%B %Y')+' · historical value')
    c[1].metric('First forecast',f'{forecast.estimate.iloc[0]:.2f}%')
    c[1].caption(forecast.target.iloc[0].strftime('%B %Y')+' · model estimate')
    c[2].metric('Selected model',meta['selected_model'].split()[0])
    c[2].caption(meta['selected_model']+' · validation winner')
    c[3].metric('Primary dataset','199 months')
    c[3].caption('January 2010 – July 2026')
    st.markdown(f'<div class="note">Forecast origin: {origin:%B %Y}. August actual data is shown separately and was not used for model selection. Evaluation is retrospective; historical release dates were not supplied.</div>',unsafe_allow_html=True)
    if meta['production_diagnostics'].get('ljung_box_p_lag12',1)<.05:
        st.warning('Model review needed: residual autocorrelation remains. Forecasts are provisional while the statistical specification is refined.')
    left,right=st.columns([3,1])
    with left:
        years=st.select_slider('History window',options=[3,5,10,17],value=5,format_func=lambda x:f'Last {x} years')
        history=data.loc[origin-pd.DateOffset(years=years):origin]
        fig=go.Figure()
        fig.add_scatter(x=history.index,y=history.inflation,name='Historical inflation',line=dict(color='#167c78',width=3))
        if forecast.lower_95.notna().all():
            fig.add_scatter(x=forecast.target,y=forecast.upper_95,line=dict(width=0),showlegend=False,hoverinfo='skip')
            fig.add_scatter(x=forecast.target,y=forecast.lower_95,fill='tonexty',fillcolor='rgba(28,136,126,.14)',line=dict(width=0),name='Conditional 95% interval')
        fig.add_scatter(x=[origin,*forecast.target],y=[data.loc[origin,'inflation'],*forecast.estimate],name='Model forecast',line=dict(color='#d4943b',width=3,dash='dot'),mode='lines+markers')
        after=data.loc[data.index>origin,'inflation'].dropna()
        fig.add_scatter(x=after.index,y=after,name='Later supplied actual',mode='markers',marker=dict(color='#213d6e',size=10,symbol='diamond'))
        fig.update_yaxes(title='Inflation (%)')
        st.plotly_chart(style(fig,'Historical trend and short-term outlook',430),width='stretch',config={'displayModeBar':False})
    with right:
        st.subheader('The next three months')
        stable_band=st.number_input('Relatively stable band (pp)',min_value=0.0,max_value=1.0,value=0.10,step=0.05,format='%.2f',
            help='A forecast within this many percentage points of the last observation at the forecast origin is labeled relatively stable. This is a display rule, not a statistical significance test.')
        for r in forecast.itertuples():
            st.metric(r.target.strftime('%B %Y'),f'{r.estimate:.2f}%')
            change=r.estimate-data.loc[origin,'inflation']
            direction='Relatively stable' if abs(change)<=stable_band else ('Rise' if change>0 else 'Fall')
            st.caption(f'{direction} · {change:+.2f} pp versus {origin:%b %Y}')
            st.caption('95% interval unavailable' if pd.isna(r.lower_95) else f'95% interval: {r.lower_95:.2f}% to {r.upper_95:.2f}%')
        st.download_button('Download forecast',forecast.to_csv(index=False),'inflation_forecast.csv','text/csv',width='stretch')
    st.caption('Inflation is year-on-year percent. Forecast errors and changes are percentage points. Model intervals do not include all parameter or data-revision uncertainty.')

elif page=='Economic indicators':
    heading('Economic indicators','Inspect the candidate predictors and their source coverage. Relationships shown here are descriptive.')
    selected_features=meta['specifications'][meta['selected_model']]['features']
    feature_labels={'exchange_rate':'PHP/USD exchange rate','policy_rate':'BSP policy rate','m3_growth':'M3 year-on-year growth'}
    st.subheader('Predictors used by the selected model')
    st.write(', '.join(feature_labels[f] for f in selected_features) if selected_features else 'The selected model uses historical inflation only.')
    st.caption('Selection uses validation forecasting error. Economic predictors use a five-month lag relative to the target month. Inclusion indicates predictive use, not a causal effect or completed stability assessment.')
    labels={'exchange_rate':'PHP/USD · monthly average','policy_rate':'BSP policy rate · percent','m3':'M3 · million PHP','m3_growth':'M3 · year-on-year growth (%)'}
    for cols in [('exchange_rate','policy_rate'),('m3','m3_growth')]:
        for panel,col in zip(st.columns(2),cols):
            with panel:
                valid=data[col].dropna()
                st.caption(f'{valid.index[0]:%b %Y} – {valid.index[-1]:%b %Y}')
                st.plotly_chart(style(px.line(data.reset_index(),x='date',y=col,color_discrete_sequence=['#16857c']),labels[col],300),width='stretch',config={'displayModeBar':False})
    st.info('Unemployment was not supplied. M3 is available through July 2026. Policy-rate history includes carried-forward decisions and requires review of regime/effective-date changes.')

elif page=='Model performance':
    heading('How the models performed','Compare identical target months at each forecast horizon. Lower error means closer historical predictions.')
    phase=st.segmented_control('Evaluation period',['validation','test'],default='test') or 'test'
    h=st.select_slider('Forecast horizon',[1,2,3],value=1,format_func=lambda x:f'{x} month'+('s' if x>1 else ''))
    subset=metrics[(metrics.phase==phase)&(metrics.horizon==h)].sort_values('RMSE')
    a,b=st.columns([1,1])
    with a:
        st.plotly_chart(style(px.bar(subset,x='RMSE',y='model',orientation='h',color_discrete_sequence=['#16857c']),f'{phase.title()} RMSE · percentage points'),width='stretch',config={'displayModeBar':False})
    with b:
        st.subheader('Error measures')
        st.dataframe(subset[['model','MAE','RMSE','N']],hide_index=True,width='stretch')
        st.caption(f'Frozen validation winner: {meta["selected_model"]}. N is the number of target months. The test ranking does not change model selection.')
    name=st.selectbox('Inspect model',list(meta['specifications']),index=list(meta['specifications']).index(meta['selected_model']))
    comparison=backtest[(backtest.phase==phase)&(backtest.horizon==h)&(backtest.model==name)]
    fig=go.Figure()
    fig.add_scatter(x=comparison.target,y=comparison.actual,name='Actual',line=dict(color='#167c78',width=3))
    fig.add_scatter(x=comparison.target,y=comparison.estimate,name='Predicted',line=dict(color='#d4943b',dash='dot',width=3))
    st.plotly_chart(style(fig,'Actual versus predicted inflation'),width='stretch',config={'displayModeBar':False})
    with st.expander('Model specification and diagnostics'):
        st.json(meta['specifications'][name])
        st.write('Selected model production diagnostics')
        st.json(meta['production_diagnostics'])
        st.caption('Nonconverged candidates are excluded from selection. Diagnostic p-values are descriptive and require review.')
        if meta['production_diagnostics'].get('ljung_box_p_lag12',1)<.05:
            st.warning('The selected fit has residual autocorrelation at lag 12 (Ljung–Box p < 0.05). It is the validation winner in this bounded grid, but has not passed full model adequacy review.')
    st.download_button('Download full evaluation',backtest.to_csv(index=False),'model_evaluation.csv','text/csv')

elif page=='Data explorer':
    heading('Explore the monthly dataset','Review the prepared observations, source coverage, and missing values before modeling.')
    span=st.date_input('Reference month range',value=(data.index[0].date(),data.index[-1].date()),min_value=data.index[0].date(),max_value=data.index[-1].date())
    columns=st.multiselect('Indicators',list(data.columns),default=list(data.columns))
    view=data[columns]
    if len(span)==2:
        view=view.loc[str(span[0]):str(span[1])]
    st.dataframe(view,width='stretch')
    st.download_button('Download selected observations',view.to_csv(),'monthly_observations.csv','text/csv')
    st.subheader('Coverage and quality')
    st.dataframe(pd.DataFrame(manifest['coverage']).T,width='stretch')
    st.caption('Blank means unavailable, not zero. M3 growth needs 12 prior months. Original source files remain unchanged.')
    with st.expander('Source file fingerprints'):
        st.dataframe(pd.DataFrame(manifest['files']),hide_index=True)
    with st.expander('Policy descriptions requiring review'):
        st.dataframe(pd.read_csv(ROOT/'data/processed/policy_review.csv'),hide_index=True)

else:
    heading('Data architecture','A traceable path from source observations to model runs, predictions, and measured errors.')
    st.markdown((ROOT/'docs/data-model.md').read_text(encoding='utf-8').split('```mermaid')[0])
    st.graphviz_chart('''digraph {rankdir=LR; node [shape=box style="rounded,filled" fillcolor="#e8f3f2" fontname="Arial" color="#16857c"];
        source_vintage -> observation; indicator -> observation; geography -> observation;
        observation -> snapshot_observation; dataset_snapshot -> snapshot_observation;
        dataset_snapshot -> model_run; model_spec -> model_run; model_run -> forecast;
        indicator -> forecast; geography -> forecast; forecast -> forecast_evaluation; observation -> forecast_evaluation;
    }''')
    st.markdown((ROOT/'docs/data-model.md').read_text(encoding='utf-8').split('```')[-1])
    with sqlite3.connect(ROOT/'database/inflation.db') as db:
        counts={t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ['observation','model_run','forecast','forecast_evaluation']}
    for col,(name,n) in zip(st.columns(4),counts.items()):
        col.metric(name.replace('_',' ').title(),f'{n:,}')
    st.download_button('Download SQL schema',(ROOT/'database/schema.sql').read_text(),'schema.sql')

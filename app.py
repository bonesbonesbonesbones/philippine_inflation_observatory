from pathlib import Path
import json
import sqlite3
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from src.analysis import LABELS, UNITS, history_narrative, relationship_pairs, correlation, relationship_narrative
from src.filters import historical_filters

ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title='Inflation Observatory',page_icon='◉',layout='wide')
st.markdown('''<style>
.stApp {background:#f8f9fa;color:#212529}
.block-container {padding-top:4.2rem;max-width:1450px}
h1,h2,h3 {letter-spacing:-.035em;color:#112c3c}
[data-testid="stSidebar"] {background:#212529;color:#e2edf1}
[data-testid="stSidebar"] * {color:#e2edf1}
[data-testid="stMetric"] {background:white;border:1px solid #e0e8ed;border-left:4px solid #0d6efd;border-radius:10px;padding:18px;min-height:120px;box-shadow:0 2px 8px #162a3c08}
[data-testid="stMetricLabel"] {color:#647787}
[data-testid="stMetricValue"] {font-size:1.4rem;color:#0b726b;white-space:normal;overflow-wrap:anywhere;line-height:1.35}
[data-testid="stColumn"] {min-width:0}
[data-testid="stMetricValue"] > div {white-space:normal;overflow-wrap:anywhere;max-width:100%;text-overflow:clip;line-height:1.3}
[data-testid="stMetricLabel"] p {white-space:normal;overflow-wrap:anywhere;text-overflow:clip;line-height:1.5}
.eyebrow {color:#0d6efd;font-size:12px;letter-spacing:.17em;font-weight:700;margin-bottom:12px}
.subtitle {color:#647787;font-size:16px;max-width:800px;margin-bottom:28px}
.note {background:#edf4ff;border-left:4px solid #0d6efd;padding:14px 18px;border-radius:6px;color:#315063;font-size:14px;margin:16px 0;line-height:1.7}
[data-testid="stSidebar"] [role="radiogroup"] label {padding:8px 12px;border-radius:8px}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {background:#0d6efd}
</style>''',unsafe_allow_html=True)

st.sidebar.markdown('## ◉ INFLATION\nOBSERVATORY')
st.sidebar.caption('PHILIPPINES / RESEARCH PROTOTYPE')
st.sidebar.divider()
page=st.sidebar.radio('Workspace',['Overview','Historical analysis','Economic indicators','Relationship analysis','Model performance','Data explorer','Data architecture'],label_visibility='collapsed')
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

# Shared live period selection; model fitting stays in notebooks.
filtered=data
if page in ['Overview','Historical analysis','Economic indicators','Relationship analysis','Data explorer']:
    filtered,start_month,end_month=historical_filters(data)

def narrative(text,title='Interpretation'):
    from html import escape
    st.markdown(f'<div class="note"><strong>{escape(title)}</strong><br>{escape(text)}</div>',unsafe_allow_html=True)

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
    latest=filtered.inflation.dropna()
    c=st.columns(4)
    change=latest.iloc[-1]-latest.iloc[0]
    c[0].metric('Period-end inflation',f'{latest.iloc[-1]:.1f}%')
    c[0].caption(f'{latest.index[-1]:%B %Y} · selected period')
    c[1].metric('Average monthly rate',f'{latest.mean():.2f}%')
    c[1].caption(f'{len(latest)} observed months · not cumulative')
    c[2].metric('Peak inflation',f'{latest.max():.1f}%')
    c[2].caption(f'{latest.idxmax():%B %Y}')
    c[3].metric('Period change',f'{change:+.2f} pp')
    c[3].caption(f'First to last selected month')
    st.markdown(f'<div class="note">Forecast origin: {origin:%B %Y}. August actual data is shown separately and was not used for model selection. Evaluation is retrospective; historical release dates were not supplied.</div>',unsafe_allow_html=True)
    if meta['production_diagnostics'].get('ljung_box_p_lag12',1)<.05:
        st.warning('Model review needed: residual autocorrelation remains. Forecasts are provisional while the statistical specification is refined.')
    left,right=st.columns([3,1])
    with left:
        st.subheader('Historical trend and forecast')
        history=filtered.loc[:origin].reindex(pd.date_range(start_month,min(end_month,origin),freq='MS'))
        # Keep historical windows on their own time axis; the fixed-origin
        # forecast must not stretch an earlier selection into 2026.
        include_forecast=False
        if origin in filtered.index:
            include_forecast=st.toggle('Overlay the July 2026 forecast',value=True)
        else:
            st.caption('Your selected history is shown on its own time axis. The July 2026 forecast is presented separately on the right.')
        fig=go.Figure()
        fig.add_scatter(x=history.index,y=history.inflation,name='Historical inflation',line=dict(color='#167c78',width=3))
        if include_forecast and forecast.lower_95.notna().all():
            fig.add_scatter(x=forecast.target,y=forecast.upper_95,line=dict(width=0),showlegend=False,hoverinfo='skip')
            fig.add_scatter(x=forecast.target,y=forecast.lower_95,fill='tonexty',fillcolor='rgba(28,136,126,.14)',line=dict(width=0),name='Conditional 95% interval')
        if include_forecast:
            fig.add_scatter(x=[origin,*forecast.target],y=[data.loc[origin,'inflation'],*forecast.estimate],name='Model forecast',line=dict(color='#d4943b',width=3,dash='dot'),mode='lines+markers')
        after=filtered.loc[filtered.index>origin,'inflation'].dropna()
        fig.add_scatter(x=after.index,y=after,name='Later supplied actual',mode='markers',marker=dict(color='#213d6e',size=10,symbol='diamond'))
        fig.update_yaxes(title='Inflation (%)')
        st.plotly_chart(style(fig,'Historical trend and short-term outlook',430),width='stretch',config={'displayModeBar':False})
        narrative(history_narrative(filtered),'Historical interpretation')
    with right:
        st.subheader('The next three months')
        st.caption(f'Fixed origin: {origin:%B %Y} · {meta["selected_model"]}')
        stable_band=st.number_input('Relatively stable band (pp)',min_value=0.0,max_value=1.0,value=0.10,step=0.05,format='%.2f',
            help='A forecast within this many percentage points of the last observation at the forecast origin is labeled relatively stable. This is a display rule, not a statistical significance test.')
        for r in forecast.itertuples():
            st.metric(r.target.strftime('%B %Y'),f'{r.estimate:.2f}%')
            change=r.estimate-data.loc[origin,'inflation']
            direction='Relatively stable' if abs(change)<=stable_band else ('Rise' if change>0 else 'Fall')
            st.caption(f'{direction} · {change:+.2f} pp versus {origin:%b %Y}')
            st.caption('95% interval unavailable' if pd.isna(r.lower_95) else f'95% interval: {r.lower_95:.2f}% to {r.upper_95:.2f}%')
        st.download_button('Download forecast',forecast.to_csv(index=False),'inflation_forecast.csv','text/csv',width='stretch')
    end_change=forecast.estimate.iloc[-1]-data.loc[origin,'inflation']
    outlook='remain relatively stable' if abs(end_change)<=stable_band else ('rise' if end_change>0 else 'fall')
    narrative(f'From the {origin:%B %Y} observation of {data.loc[origin,"inflation"]:.1f}%, the selected {meta["selected_model"]} estimates {forecast.estimate.iloc[0]:.2f}%, {forecast.estimate.iloc[1]:.2f}% and {forecast.estimate.iloc[2]:.2f}% for the next three months. By {forecast.target.iloc[-1]:%B %Y}, inflation is projected to {outlook} ({end_change:+.2f} percentage points versus the origin). This classification uses the selected stability band. Remaining residual autocorrelation and unavailable release histories limit reliability.','Forecast interpretation')
    st.caption('Inflation is year-on-year percent. Forecast errors and changes are percentage points. Model intervals do not include all parameter or data-revision uncertainty.')

elif page=='Historical analysis':
    heading('Historical inflation analysis','Filter the historical record, compare years, and inspect the monthly observations behind each summary.')
    s=filtered.inflation.dropna()
    k=st.columns(4)
    k[0].metric('Selected months',len(s))
    k[1].metric('Average monthly rate',f'{s.mean():.2f}%')
    k[2].metric('Peak rate',f'{s.max():.1f}%')
    k[3].metric('First-to-last change',f'{s.iloc[-1]-s.iloc[0]:+.2f} pp')
    narrative(history_narrative(filtered))
    tabs=st.tabs(['Monthly history','Compare years','Historical records'])
    with tabs[0]:
        plot=filtered.reindex(pd.date_range(start_month,end_month,freq='MS')).rename_axis('date').reset_index()
        st.plotly_chart(style(px.line(plot,x='date',y='inflation',labels={'inflation':'Inflation (%)'},color_discrete_sequence=['#0d6efd']),'Selected monthly inflation',420),width='stretch',config={'displayModeBar':False})
    with tabs[1]:
        comparison=filtered.reset_index()
        comparison['Year']=comparison.date.dt.year.astype(str)
        comparison['Month']=comparison.date.dt.month
        # Complete each year's calendar to avoid connecting across excluded months.
        comparison=comparison.set_index(['Year','Month']).reindex(pd.MultiIndex.from_product([comparison.Year.unique(),range(1,13)],names=['Year','Month'])).reset_index()
        fig=px.line(comparison,x='Month',y='inflation',color='Year',labels={'inflation':'Inflation (%)'})
        fig.update_xaxes(tickmode='array',tickvals=list(range(1,13)),ticktext=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])
        st.plotly_chart(style(fig,'Monthly rates by year',480),width='stretch',config={'displayModeBar':False})
        st.caption('Each line is a year-on-year inflation rate for that month. Months are not added together. Missing months remain gaps.')
    with tabs[2]:
        st.dataframe(filtered,width='stretch')
        st.download_button('Download filtered history',filtered.to_csv(),'filtered_history.csv','text/csv')

elif page=='Economic indicators':
    heading('Economic indicators','Inspect the candidate predictors and their source coverage. Relationships shown here are descriptive.')
    selected_features=meta['specifications'][meta['selected_model']]['features']
    feature_labels={'exchange_rate':'PHP/USD exchange rate','policy_rate':'BSP policy rate','m3_growth':'M3 year-on-year growth'}
    st.subheader('Predictors used by the selected model')
    st.write(', '.join(feature_labels[f] for f in selected_features) if selected_features else 'The selected model uses historical inflation only.')
    st.caption('Selection uses validation forecasting error. Economic predictors use a five-month lag relative to the target month. Inclusion indicates predictive use, not a causal effect or completed stability assessment.')
    labels={'exchange_rate':'PHP/USD · monthly average','policy_rate':'BSP policy rate · percent','m3':'M3 · million PHP','m3_growth':'M3 · year-on-year growth (%)'}
    indicator_cards=st.columns(4)
    for card,col in zip(indicator_cards,labels):
        observed=filtered[col].dropna()
        card.metric(LABELS[col],'Unavailable' if observed.empty else f'{observed.iloc[-1]:,.2f}')
        card.caption(UNITS[col]+(' · no selected observations' if observed.empty else f' · {observed.index[-1]:%b %Y}'))
    for cols in [('exchange_rate','policy_rate'),('m3','m3_growth')]:
        for panel,col in zip(st.columns(2),cols):
            with panel:
                valid=filtered[col].dropna()
                if valid.empty:
                    st.info(f'No {LABELS[col]} observations in the selected period.')
                    continue
                st.caption(f'{valid.index[0]:%b %Y} – {valid.index[-1]:%b %Y}')
                plot=filtered.reindex(pd.date_range(start_month,end_month,freq='MS')).rename_axis('date').reset_index()
                st.plotly_chart(style(px.line(plot,x='date',y=col,color_discrete_sequence=['#0d6efd']),labels[col],300),width='stretch',config={'displayModeBar':False})
                narrative(f'{LABELS[col]} moved from {valid.iloc[0]:,.2f} to {valid.iloc[-1]:,.2f} {UNITS[col]} across {len(valid)} available selected months. This is an observed first-to-last change; it does not establish its effect on inflation.')
    st.info('Unemployment was not supplied. M3 is available through July 2026. Policy-rate history includes carried-forward decisions and requires review of regime/effective-date changes.')

elif page=='Relationship analysis':
    heading('Relationship analysis','Explore contemporaneous and lagged associations between inflation and economic indicators within the selected historical period.')
    opts=st.columns(4)
    indicator=opts[0].selectbox('Economic indicator',['exchange_rate','policy_rate','m3_growth','m3'],format_func=lambda c:LABELS[c],key='relationship_indicator')
    transform=opts[1].selectbox('Analyze',['Monthly changes','Levels'],key='relationship_transform')
    method=opts[2].selectbox('Correlation method',['pearson','spearman'],format_func=str.title,key='relationship_method')
    lag=opts[3].number_input('Indicator lag (months)',min_value=0,max_value=12,value=0,step=1,key='relationship_lag')
    changes=transform=='Monthly changes'
    pairs=relationship_pairs(data,filtered.index,indicator,int(lag),changes)
    r=correlation(pairs,method)
    k=st.columns(4)
    k[0].metric('Paired months',len(pairs))
    k[1].metric(method.title()+' correlation','Unavailable' if r is None else f'{r:+.3f}')
    k[2].metric('Indicator timing','Same month' if lag==0 else f'{lag} months earlier')
    k[3].metric('Paired coverage',f'{100*len(pairs)/len(filtered):.0f}%')
    k[3].caption(f'{len(pairs)} of {len(filtered)} selected target months')
    narrative(relationship_narrative(pairs,indicator,int(lag),method,changes))
    st.caption('Monthly changes are first differences in each original unit (percentage-point changes for percent series). Lags are aligned on the full calendar before selecting inflation months; the paired indicator month can precede the filter window. Correlations are descriptive, with no independent-sample significance claim.')
    if len(pairs):
        display_pairs=pairs.reset_index().rename(columns={'index':'date'})
        unit='monthly change' if changes else UNITS[indicator]
        fig=px.scatter(display_pairs,x='indicator',y='inflation',hover_data=['date','source_month'],labels={'indicator':LABELS[indicator]+f' ({unit})','inflation':'Inflation change (pp)' if changes else 'Inflation (%)'},color_discrete_sequence=['#0d6efd'])
        st.plotly_chart(style(fig,'Paired observations',430),width='stretch',config={'displayModeBar':False})
    tabs=st.tabs(['Lag comparison','Correlation matrix','Paired records'])
    with tabs[0]:
        rows=[]
        for candidate_lag in range(13):
            sample=relationship_pairs(data,filtered.index,indicator,candidate_lag,changes)
            rows.append({'Lag (months)':candidate_lag,'Correlation':correlation(sample,method),'Paired months':len(sample)})
        lag_table=pd.DataFrame(rows)
        fig=px.bar(lag_table,x='Lag (months)',y='Correlation',color_discrete_sequence=['#0d6efd'],range_y=[-1,1])
        st.plotly_chart(style(fig,'Association across calendar lags'),width='stretch',config={'displayModeBar':False})
        st.dataframe(lag_table,hide_index=True,width='stretch')
        st.caption('Sample counts can differ by lag. Searching many lags can produce chance patterns; this view does not select predictors or tune the forecasting model.')
    with tabs[1]:
        fields=['inflation','exchange_rate','policy_rate','m3_growth']
        matrix_data=data[fields].diff() if changes else data[fields]
        matrix_data=matrix_data.loc[filtered.index]
        matrix=matrix_data.corr(method=method,min_periods=3)
        counts=matrix_data.notna().astype(int).T.dot(matrix_data.notna().astype(int))
        fig=go.Figure(go.Heatmap(z=matrix.values,x=[LABELS[c] for c in fields],y=[LABELS[c] for c in fields],zmin=-1,zmax=1,colorscale='RdBu',reversescale=True,text=matrix.round(2).values,texttemplate='%{text}',customdata=counts.values,hovertemplate='%{y} / %{x}<br>r=%{z:.3f}<br>Paired months=%{customdata}<extra></extra>'))
        st.plotly_chart(style(fig,'Same-month correlation matrix',500),width='stretch',config={'displayModeBar':False})
        st.caption('The matrix always uses same-month values; the lag control applies to the selected pair and lag comparison. Blank cells indicate insufficient data or no variation. Hover for paired-month counts.')
    with tabs[2]:
        st.dataframe(pairs,width='stretch')
        st.download_button('Download paired observations',pairs.to_csv(),'relationship_pairs.csv','text/csv')

elif page=='Model performance':
    heading('How the models performed','Compare identical target months at each forecast horizon. Lower error means closer historical predictions.')
    phase=st.segmented_control('Evaluation period',['validation','test'],default='test') or 'test'
    h=st.select_slider('Forecast horizon',[1,2,3],value=1,format_func=lambda x:f'{x} month'+('s' if x>1 else ''))
    subset=metrics[(metrics.phase==phase)&(metrics.horizon==h)].sort_values('RMSE')
    score=subset.loc[subset.model==meta['selected_model']].iloc[0]
    score_cards=st.columns(3)
    score_cards[0].metric('Selected model MAE',f'{score.MAE:.3f} pp')
    score_cards[1].metric('Selected model RMSE',f'{score.RMSE:.3f} pp')
    score_cards[2].metric('Evaluation months',int(score.N))
    a,b=st.columns([1,1])
    with a:
        st.plotly_chart(style(px.bar(subset,x='RMSE',y='model',orientation='h',color_discrete_sequence=['#16857c']),f'{phase.title()} RMSE · percentage points'),width='stretch',config={'displayModeBar':False})
    with b:
        st.subheader('Error measures')
        st.dataframe(subset[['model','MAE','RMSE','N']],hide_index=True,width='stretch')
        st.caption(f'Frozen validation winner: {meta["selected_model"]}. N is the number of target months. The test ranking does not change model selection.')
    selected_score=subset.loc[subset.model==meta['selected_model']].iloc[0]
    naive_score=subset.loc[subset.model=='Naive'].iloc[0]
    improvement=100*(naive_score.RMSE-selected_score.RMSE)/naive_score.RMSE if naive_score.RMSE else None
    comparison_text=(f'{abs(improvement):.1f}% '+('lower' if improvement>=0 else 'higher')+' than the naive benchmark') if improvement is not None else 'not comparable with a zero-error naive baseline'
    narrative(f'For {int(selected_score.N)} {phase} target months at the {h}-month horizon, the selected model has MAE {selected_score.MAE:.3f} and RMSE {selected_score.RMSE:.3f} percentage points. Its RMSE is {comparison_text}. MAE describes the average absolute error; RMSE penalizes larger errors more strongly. Results describe this supplied data vintage and evaluation period, not guaranteed future accuracy.','Performance interpretation')
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
    columns=st.multiselect('Indicators',list(data.columns),default=list(data.columns))
    if not columns:
        st.info('Choose at least one indicator to view or download observations.')
        st.stop()
    view=filtered[columns]
    table_cards=st.columns(3)
    table_cards[0].metric('Selected records',len(view))
    table_cards[1].metric('Complete records',int(view.notna().all(axis=1).sum()))
    table_cards[2].metric('Missing values',int(view.isna().sum().sum()))
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

"""One persistent historical selection, shared by every analytical view."""
import pandas as pd
import streamlit as st

MODES=['Last 12 months','Last 3 years','Latest year','Choose years','Custom range','All history']

def resolve_window(index,mode,years=None,custom=None):
    index=pd.DatetimeIndex(index).sort_values()
    first,last=index[0],index[-1]
    if mode=='Last 12 months':
        start,end=max(first,last-pd.DateOffset(months=11)),last
    elif mode=='Last 3 years':
        start,end=max(first,last-pd.DateOffset(months=35)),last
    elif mode=='Latest year':
        start,end=max(first,pd.Timestamp(last.year,1,1)),last
    elif mode=='Choose years':
        chosen=index[index.year.isin(years or [])]
        return chosen
    elif mode=='Custom range':
        start,end=map(pd.Timestamp,custom)
        start,end=start.to_period('M').to_timestamp(),end.to_period('M').to_timestamp()
    else:
        start,end=first,last
    return index[(index>=start)&(index<=end)]

def shift_window(index,start,end,direction):
    """Move a full window, clamping at source bounds without shrinking it."""
    index=pd.DatetimeIndex(index)
    left,right=index.get_loc(start),index.get_loc(end)
    length=right-left+1
    new_left=max(0,min(left+direction*length,len(index)-length))
    return index[new_left],index[new_left+length-1]

def historical_filters(data):
    months=pd.DatetimeIndex(data.index)
    all_years=sorted(set(months.year),reverse=True)
    if 'history_filter_state' not in st.session_state:
        st.session_state.history_filter_state={'mode':'Last 3 years','years':all_years[:2],
            'custom':(max(months[0],months[-1]-pd.DateOffset(months=35)),months[-1])}
    state=st.session_state.history_filter_state
    # Restore widget values after pages without historical controls clean them up.
    if 'history_mode_ui' not in st.session_state:
        st.session_state.history_mode_ui=state['mode']
    if 'history_years_ui' not in st.session_state:
        st.session_state.history_years_ui=state['years']
    if 'history_dates_ui' not in st.session_state:
        st.session_state.history_dates_ui=tuple(d.date() for d in state['custom'])
    slider_key=f"history_slider_ui_{state.get('revision',0)}"

    def set_window(start,end):
        state['mode']='Custom range'
        state['custom']=(start,end)
        st.session_state.history_mode_ui='Custom range'
        st.session_state.history_dates_ui=(start.date(),end.date())
        # A fresh slider instance gets a range default after external date edits;
        # no competing default and programmatic widget value are supplied.
        state['revision']=state.get('revision',0)+1

    def mode_changed():
        if st.session_state.history_mode_ui is None:
            st.session_state.history_mode_ui=state['mode']
            return
        old=resolve_window(months,state['mode'],state['years'],state['custom'])
        state['mode']=st.session_state.history_mode_ui
        if state['mode']=='Custom range' and len(old):
            set_window(old[0],old[-1])

    def dates_changed():
        dates=st.session_state.history_dates_ui
        if len(dates)==2:
            start,end=[pd.Timestamp(d).to_period('M').to_timestamp() for d in dates]
            if start<=end:
                set_window(start,end)

    def slider_changed():
        set_window(*st.session_state[slider_key])

    def years_changed():
        state['years']=st.session_state.history_years_ui

    def reset():
        state['mode']='All history'
        st.session_state.history_mode_ui='All history'

    def move(direction):
        current=resolve_window(months,state['mode'],state['years'],state['custom'])
        set_window(*shift_window(months,current[0],current[-1],direction))

    with st.container(border=True):
        top=st.columns([5,1])
        top[0].markdown('**Explore a historical period**')
        top[1].button('Reset all',key='history_reset',on_click=reset,width='stretch')
        st.segmented_control('Quick period',MODES,key='history_mode_ui',on_change=mode_changed,
            help='Periods end at the latest supplied observation, not today. Select Custom range for exact dates or a draggable month range.')
        # A deselected segmented control must still resolve to its prior mode.
        mode=st.session_state.history_mode_ui or state['mode']
        state['mode']=mode
        if mode=='Choose years':
            st.multiselect('Which years would you like to compare?',all_years,key='history_years_ui',on_change=years_changed,
                placeholder='Select one or more years')
            st.caption('All available months in each selected year are included. Other date limits do not apply.')
        elif mode=='Custom range':
            st.date_input('Choose start and end dates',min_value=months[0].date(),max_value=(months[-1]+pd.offsets.MonthEnd(0)).date(),
                key='history_dates_ui',on_change=dates_changed,format='YYYY-MM-DD')
            st.select_slider('Or drag the month range',options=list(months),value=state['custom'],key=slider_key,
                format_func=lambda d:d.strftime('%b %Y'),on_change=slider_changed)
            st.caption('Whole calendar months are included. Date fields and the range slider stay synchronized.')
            if len(st.session_state.history_dates_ui)!=2:
                st.info('Select an end date to finish the range. Your last complete selection remains visible below.')

        selected=resolve_window(months,mode,state['years'],state['custom'])
        if not len(selected):
            st.info('Select at least one year above, or choose a quick period. No unrelated observations are substituted.')
            st.stop()
        start,end=selected[0],selected[-1]
        contiguous=len(selected)==len(pd.date_range(start,end,freq='MS'))
        nav=st.columns([1,3,1])
        nav[0].button('← Previous',key='history_previous',disabled=not contiguous or start==months[0],on_click=move,args=(-1,),width='stretch',help='Move backward by the length of this period.')
        text=f'{start:%b %Y} – {end:%b %Y}'
        if not contiguous:
            text='Years '+', '.join(map(str,sorted(state['years'])))
        nav[1].markdown(f'**{text} · {len(selected)} months**')
        nav[2].button('Next →',key='history_next',disabled=not contiguous or end==months[-1],on_click=move,args=(1,),width='stretch',help='Move forward by the length of this period.')
        st.caption('Charts, historical summaries, relationship calculations and downloads update immediately. Your period carries between pages. Forecast origin and model evaluation remain fixed.')
        recent=data.loc[selected,'inflation'].dropna()
        if len(recent):
            st.caption(f'Period-end inflation: {recent.iloc[-1]:.1f}% · Average monthly rate: {recent.mean():.2f}% · Latest supplied month: {months[-1]:%B %Y}')
    return data.loc[selected],start,end

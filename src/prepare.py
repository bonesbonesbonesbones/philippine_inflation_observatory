"""Read supplied files without modifying originals; export monthly analytical data."""
from pathlib import Path
import hashlib
import json
import re
import pandas as pd
import openpyxl

ROOT = Path(__file__).resolve().parents[1]

def prepare():
    raw = ROOT / 'data/raw'
    out = ROOT / 'data/processed'
    out.mkdir(parents=True, exist_ok=True)
    frames = []
    for file in sorted(raw.glob('*.csv')):
        wide = pd.read_csv(file, sep=';', skiprows=2, na_values=['..'])
        row = wide.loc[(wide.Geolocation == 'PHILIPPINES') & (wide['Commodity Description'] == '0 - ALL ITEMS')]
        assert len(row) == 1, 'Expected one national all-items row'
        s = row.iloc[0, 2:]
        s.index = pd.to_datetime(s.index, format='%Y %b')
        frames.append(pd.to_numeric(s, errors='raise'))
    inflation = pd.concat(frames).sort_index().dropna().rename('inflation')
    assert not inflation.index.duplicated().any()
    fx = []
    year = None
    for r in openpyxl.load_workbook(raw/'pesodollar.xlsx', data_only=True)['monthly'].values:
        if isinstance(r[1], (int,float)) and 1900 < r[1] < 2100:
            year = int(r[1])
        if year and isinstance(r[2],str) and isinstance(r[3],(int,float)):
            try:
                date = pd.to_datetime(f'{year} {r[2].strip()}', format='%Y %B')
                fx.append((date,r[3]))
            except ValueError:
                pass
    exchange = pd.DataFrame(fx,columns=['date','exchange_rate']).set_index('date').exchange_rate
    sheet = openpyxl.load_workbook(raw/'dcs_srf.xlsx',data_only=True).active
    # Level row, not M4, M3/GDP, or the separately published growth row.
    assert 'M3 (M2' in str(sheet.cell(25,3).value)
    money = []
    for c in range(1,sheet.max_column+1):
        label, value = sheet.cell(5,c).value, sheet.cell(25,c).value
        if not isinstance(value,(int,float)):
            continue
        if hasattr(label,'year'):
            date = pd.Timestamp(label)
        elif isinstance(label,str) and re.match(r'^[A-Za-z]{3}-\d{2}',label):
            date = pd.to_datetime(label[:6],format='%b-%y')
        else:
            continue
        money.append((date,value))
    m3 = pd.DataFrame(money,columns=['date','m3']).set_index('date').m3
    decisions, review = [], []
    for i,r in enumerate(openpyxl.load_workbook(raw/'MonetaryPolicyDecisions.xlsx',data_only=True).active.values,1):
        if not r[0] or not re.match(r'^\d{4}-\d{2}-\d{2}',str(r[0])):
            continue
        text = str(r[1])
        # Restrict to first policy/borrowing-rate clause, before lending/deposit rates.
        head = text.split('percent')[0]
        matches = re.findall(r'(?:to|at)\s+(\d+(?:\.\d+)?)\s*$',head)
        if matches:
            decisions.append((pd.Timestamp(r[0]),float(matches[-1])))
        else:
            review.append({'row':i,'date':str(r[0]),'description':text})
    pd.DataFrame(review,columns=['row','date','description']).to_csv(out/'policy_review.csv',index=False)
    policy = pd.DataFrame(decisions,columns=['date','policy_rate']).sort_values('date').set_index('date')
    # Last observed decision within month; carry forward only from earlier decisions.
    policy.index = policy.index.to_period('M').to_timestamp()
    policy = policy.groupby(level=0).last().reindex(pd.date_range('2010-01-01','2026-08-01',freq='MS')).ffill().policy_rate
    df = pd.concat([inflation,exchange,m3,policy],axis=1).loc['2010-01-01':'2026-08-01'].asfreq('MS')
    df['m3_growth'] = df.m3.pct_change(12,fill_method=None)*100
    df.index.name = 'date'
    df.to_csv(out/'monthly.csv')
    manifest = {'files':[{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in sorted(raw.iterdir())],
        'policy_rows_requiring_review':len(review), 'coverage':{c:{'start':str(df[c].first_valid_index()),'end':str(df[c].last_valid_index()),'missing':int(df[c].isna().sum())} for c in df},
        'notes':['User-supplied source files; not independently authenticated.','Source vintage is the supplied file hash; original release dates are unavailable.','Policy rate extracted from decision text: review policy_review.csv before research use.','ms.xls retained for reconciliation; primary M3 comes from DCS level row 25.','Unemployment not supplied.','Model experiment ends July 2026; August inflation is available for display.']}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    return df, manifest

if __name__ == '__main__':
    df, manifest = prepare()
    print(df.tail().to_string())
    print(json.dumps(manifest['coverage'],indent=2))
    print('Policy rows requiring review:',manifest['policy_rows_requiring_review'])

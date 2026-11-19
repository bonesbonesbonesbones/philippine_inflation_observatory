"""Expose basic cleaning checks in the separate simple experiment."""
from pathlib import Path
import nbformat as nb
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'notebooks/03_simple_forecasting_experiment.ipynb'
n=nb.read(path,as_version=4)
if any('Inspect raw file structure' in c.source for c in n.cells):
    raise SystemExit('Cleaning sections already inserted')
inspection=[nb.v4.new_markdown_cell('''## Inspect raw file structure
Before cleaning, view the original columns and a few rows. The CSV month columns must be turned into rows. The exchange-rate workbook has headings, blank rows and repeated year labels. We select only the required fields; no original file is overwritten.'''),
nb.v4.new_code_cell('''raw_inflation = pd.read_csv(RAW / "Dataset-12019-2026.csv", sep=";", skiprows=2, na_values=[".."])
print("Raw inflation shape:", raw_inflation.shape)
display(raw_inflation.iloc[:, :8].head())
raw_exchange = pd.read_excel(RAW / "pesodollar.xlsx", sheet_name="monthly", header=None)
display(raw_exchange.iloc[:14, :5])''')]
# Insert after imports, before the first source cleaning section.
n.cells[2:2]=inspection
position=next(i for i,c in enumerate(n.cells) if c.cell_type=='markdown' and '## 3. View' in c.source)
n.cells[position:position]=[
nb.v4.new_markdown_cell('''## Cleaning check before modeling
The cleaning steps above remove non-data spreadsheet rows, strip month-label spaces, turn dates/numbers into usable types, and join matching months. Here we check the result. Missing source observations and conflicting duplicate months should be reviewed, not hidden by filling or keeping an arbitrary row. We do not remove inflation spikes merely because they are large: they can be real observations.'''),
nb.v4.new_code_cell('''cleaning_check = pd.DataFrame({
    "check": ["Monthly records", "Duplicate dates", "Missing inflation", "Missing exchange rate",
              "Nonpositive exchange rates", "Expected months"],
    "result": [len(data), int(data.index.duplicated().sum()), int(data["inflation"].isna().sum()),
               int(data["exchange_rate"].isna().sum()), int(data["exchange_rate"].le(0).sum()), 199]
})
display(cleaning_check)
display(data.dtypes.rename("data type").to_frame())
assert data.index.equals(pd.date_range("2010-01-01", "2026-07-01", freq="MS", name="date"))
assert data["exchange_rate"].gt(0).all()
print("Cleaning complete: 199 unique, continuous months with both required variables.")
print("No inflation interpolation, outlier deletion or artificial exchange-rate filling was used.")''')]
nb.write(n,path)
print('Added raw inspection and explicit cleaning/preparation checks.')

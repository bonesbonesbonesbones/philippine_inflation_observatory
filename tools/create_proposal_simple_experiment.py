"""Create a plain-language, proposal-aligned experiment; preserve earlier work."""
from pathlib import Path
import nbformat as nb
import textwrap
ROOT=Path(__file__).resolve().parents[1]
cells=[]
def md(s):cells.append(nb.v4.new_markdown_cell(textwrap.dedent(s).strip()))
def code(s):cells.append(nb.v4.new_code_cell(textwrap.dedent(s).strip()))
md('''# Philippine inflation forecasting - simple proposal experiment
**DATA CLEANING -> DATA PREPARATION -> MODELING -> RESULTS**

Predict Philippine national headline inflation one, two and three months ahead using historical inflation and the proposal's core indicators: PHP/USD exchange rate, BSP policy rate and M3 money supply.

The code is written directly in this notebook. There are no local `src` imports and no web app/database steps. Earlier experiments stay unchanged. Use the project's `.venv` kernel and run from top to bottom.

This notebook follows the example's short, numbered sections and explanations. It uses the proposal's forecasting methods, not the unrelated classification/clustering algorithms in the example.''')
md('''## A. DATA CLEANING
### A1. Import the libraries and locate the files
`pandas` reads tables, `numpy` handles numbers, `matplotlib` draws plots, and `SARIMAX` fits both SARIMA and SARIMAX. `re` extracts rates from policy text.''')
code('''from pathlib import Path
from datetime import datetime
import calendar
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from IPython.display import display, Markdown
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.stats.diagnostic import acorr_ljungbox

ROOT = Path.cwd() if (Path.cwd() / "data/raw").exists() else Path.cwd().parent
RAW = ROOT / "data/raw"
OUT = ROOT / "artifacts/proposal_simple_experiment"
OUT.mkdir(parents=True, exist_ok=True)
get_ipython().run_line_magic("matplotlib", "inline")
plt.rcParams.update({"figure.figsize": (11, 4), "figure.dpi": 110,
                     "axes.grid": True, "grid.alpha": 0.2})''')
md('''### A2. Inspect the raw data
Look at the original headings and rows before cleaning. The inflation files store months in columns. The spreadsheets contain headings and blank cells that are not observations.''')
code('''sample = pd.read_csv(RAW / "Dataset-12019-2026.csv", sep=";", skiprows=2, na_values=[".."])
display(sample.iloc[:, :8].head())
exchange_sheet = pd.read_excel(RAW / "pesodollar.xlsx", sheet_name="monthly", header=None)
policy_sheet = pd.read_excel(RAW / "MonetaryPolicyDecisions.xlsx", header=None)
money_sheet = pd.read_excel(RAW / "dcs_srf.xlsx", header=None)
display(exchange_sheet.iloc[:12, :5], policy_sheet.head(5), money_sheet.iloc[:6, :14])''')
md('''### A3. Clean national headline inflation
Keep the Philippines all-items row. Convert month headings to dates and values to numbers. `..` means missing, not zero. Both supplied CSVs state the same 2018=100 basis. Inflation is already a year-on-year percent, so do not calculate another percent change.''')
code('''parts = []
for filename in ["Dataset-11995-2018.csv", "Dataset-12019-2026.csv"]:
    table = pd.read_csv(RAW / filename, sep=";", skiprows=2, na_values=[".."])
    row = table[(table["Geolocation"] == "PHILIPPINES") &
                (table["Commodity Description"] == "0 - ALL ITEMS")]
    assert len(row) == 1, "Expected one national all-items row"
    values = row.iloc[0, 2:]
    values.index = pd.to_datetime(values.index, format="%Y %b")
    parts.append(pd.to_numeric(values, errors="raise"))

inflation = pd.concat(parts).sort_index().rename("inflation")
assert inflation.index.is_unique, "Review duplicate inflation months"
display(inflation.to_frame().tail(8))''')
md('''### A4. Clean the monthly average exchange rate
Use the `Average` column in the `monthly` sheet. Fill only the repeated year labels; do not invent missing exchange-rate values. Remove headings and other rows that have no valid month and numeric rate.''')
code('''exchange = exchange_sheet.iloc[:, [1, 2, 3]].copy()
exchange.columns = ["year", "month", "exchange_rate"]
exchange["year"] = pd.to_numeric(exchange["year"], errors="coerce").ffill()
month_numbers = {name: number for number, name in enumerate(calendar.month_name) if name}
exchange["month"] = exchange["month"].astype(str).str.strip().map(month_numbers)
exchange["exchange_rate"] = pd.to_numeric(exchange["exchange_rate"], errors="coerce")
exchange = exchange.dropna(subset=["year", "month", "exchange_rate"])
exchange["date"] = pd.to_datetime(dict(year=exchange["year"].astype(int),
                                     month=exchange["month"].astype(int), day=1))
exchange = exchange.set_index("date")["exchange_rate"].sort_index()
assert exchange.index.is_unique
display(exchange.to_frame().tail())''')
md('''### A5. Clean M3 money supply
The supplied DCS sheet has date labels in Excel row 5 and **M3 levels** in row 25. Pandas uses positions 4 and 24 because it starts counting at zero. Do not use the M4 or M3/GDP rows. Labels such as `Jul-26 p` include a provisional marker; keep the month part for joining dates. Raw files are unchanged.''')
code('''assert "M3 (M2" in str(money_sheet.iloc[24, 2]), "Check the M3 source row"
money_rows = []
for label, value in zip(money_sheet.iloc[4], money_sheet.iloc[24]):
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        continue
    if isinstance(label, (pd.Timestamp, datetime)):
        date = pd.Timestamp(label)
    elif isinstance(label, str) and re.match(r"^[A-Za-z]{3}-\\d{2}", label):
        date = pd.to_datetime(label[:6], format="%b-%y")
    else:
        continue
    money_rows.append({"date": date, "m3": number})

money = pd.DataFrame(money_rows).set_index("date")["m3"].sort_index()
assert money.index.is_unique
display(money.to_frame().tail())'''.replace('\\\\d','\\d'))
md('''### A6. Clean the BSP policy-rate decisions
The file contains decision text, not a ready monthly table. Read the first rate stated before `percent`, after `at` or `to`; this avoids later deposit/lending rates. Keep descriptions without a numeric match for review. Use the last decision in each month and carry the last known rate forward when there is no new numeric decision.

This simple text rule needs manual checking, especially exact effective dates and the 2016 policy-framework change. It is not a complete policy-history audit.''')
code('''policy_rows = []
policy_review = []
for date_text, description in policy_sheet.iloc[:, :2].itertuples(index=False, name=None):
    if not re.match(r"^\\d{4}-\\d{2}-\\d{2}", str(date_text)):
        continue
    first_rate_text = str(description).split("percent")[0]
    match = re.search(r"(?:at|to)\\s+(\\d+(?:\\.\\d+)?)\\s*$", first_rate_text)
    if match:
        policy_rows.append({"date": pd.Timestamp(date_text), "policy_rate": float(match.group(1))})
    else:
        policy_review.append({"date": date_text, "description": description})

policy = pd.DataFrame(policy_rows).sort_values("date").set_index("date")
policy.index = policy.index.to_period("M").to_timestamp()
policy = policy.groupby(level=0).last()
policy = policy.reindex(pd.date_range("2010-01-01", "2026-07-01", freq="MS")).ffill()
policy = policy["policy_rate"]
display(pd.DataFrame(policy_review), policy.to_frame().tail())
pd.DataFrame(policy_review).to_csv(OUT / "policy_review.csv", index=False)'''.replace('\\\\','\\'))
md('''## B. DATA PREPARATION
### B1. Join the four monthly series and check them
Use January 2010–July 2026: 199 months, matching the proposal's intended primary period. Keep one national row per month. Check missing values and duplicate dates; stop for review rather than fill inflation/M3 or delete real inflation spikes. `ms.xls` ends before this period, so it is not needed. Unemployment was not supplied and is not added artificially.''')
code('''data = pd.concat([inflation, exchange, policy, money], axis=1).sort_index()
data = data.loc["2010-01-01":"2026-07-01"].asfreq("MS")
data.index.name = "date"
display(data.head(), data.tail())
display(data.isna().sum().rename("missing values").to_frame())
print("Rows:", len(data), "| Duplicate dates:", data.index.duplicated().sum())
assert len(data) == 199 and data.index.is_unique
assert data.notna().all().all(), "Review missing source data"
assert data.index.equals(pd.date_range("2010-01-01", "2026-07-01", freq="MS", name="date"))
assert data[["exchange_rate", "m3"]].gt(0).all().all()
print("Passed: 199 continuous months; all four source series are present.")''')
md('''### B2. Prepare M3 growth and older indicator values
M3 is in million pesos. Convert it to annual growth: `100 × (this month / same month last year − 1)`.

For each target month, use indicators from **five months earlier**. At a three-month horizon this is two months before the origin, so actual future indicators are not supplied. This is a stated reporting-delay assumption; original release dates and older data versions were not supplied.

The first twelve rows cannot have M3 growth; lagging loses five more. Remove only this expected starting gap. All models use the same remaining 182 months.''')
code('''data["m3_growth"] = data["m3"].pct_change(12, fill_method=None) * 100
inputs = ["exchange_rate", "policy_rate", "m3_growth"]
lag_columns = ["exchange_lag5", "policy_lag5", "m3_growth_lag5"]
data[lag_columns] = data[inputs].shift(5)
model_data = data.dropna(subset=["inflation"] + lag_columns).copy()
assert len(model_data) == 182
assert model_data.index[0] == pd.Timestamp("2011-06-01")
display(model_data[["inflation"] + lag_columns].head())
data.to_csv(OUT / "prepared_data.csv")''')
md('''### B3. Plot the prepared series
Each variable has its own units. These plots describe history; they do not show cause and effect.''')
code('''fig, axes = plt.subplots(4, 1, figsize=(11, 9), sharex=True)
for axis, column, unit in zip(axes, ["inflation"] + inputs,
                            ["Inflation (% YoY)", "PHP per USD", "Policy rate (%)", "M3 growth (% YoY)"]):
    axis.plot(data.index, data[column], color="black")
    axis.set_ylabel(unit)
axes[0].set_title("Prepared monthly data")
axes[-1].set_xlabel("Reference month")
fig.tight_layout()
fig.savefig(OUT / "01_prepared_data.png")
plt.show()
plt.close(fig)''')
md('''### B4. Keep dates in order
Use twelve validation target months before the final twenty-four target months. Choose a model using validation errors only. Report the final block afterwards without changing that choice. No random train/test split.

These historical months were already seen in earlier experiments. They are **not a fresh untouched test**. This is a simpler, proposal-aligned comparison on the same supplied files, not new independent proof.''')
code('''validation_months = model_data.index[-36:-24]
test_months = model_data.index[-24:]
display(pd.DataFrame({
    "block": ["Validation", "Previously seen final test"],
    "first target": [validation_months[0], test_months[0]],
    "last target": [validation_months[-1], test_months[-1]],
    "months per horizon": [len(validation_months), len(test_months)]
}))''')
md('''## C. MODELING
### C1. Define the comparisons
**Naive:** repeat the latest inflation value. **Seasonal naive:** use the same month last year.
**SARIMA:** use inflation history. **SARIMAX:** add older economic indicators.

Test each indicator separately, then all three together, as the proposal requires. This is a small fixed comparison, not a large search for the best settings. Order `(1,0,0)` uses one past-value term, no differencing and no error term. Seasonal `(1,0,0,12)` uses a twelve-month seasonal term. The model includes an intercept.

For SARIMAX, subtract each training-column mean and divide by its training standard deviation so the units have comparable scales. Apply those same training numbers to future inputs. Do not use future data when calculating them.''')
code('''models = {
    "Naive": [],
    "Seasonal naive": [],
    "SARIMA": [],
    "SARIMAX exchange": ["exchange_lag5"],
    "SARIMAX policy": ["policy_lag5"],
    "SARIMAX M3": ["m3_growth_lag5"],
    "SARIMAX combined": lag_columns
}
display(pd.DataFrame({"model": list(models), "older indicators used": list(models.values())}))

def make_forecast(name, train, future_x):
    dates = future_x.index
    if name == "Naive":
        return np.repeat(train["inflation"].iloc[-1], len(dates)), None
    if name == "Seasonal naive":
        values = [train.loc[date - pd.DateOffset(years=1), "inflation"] for date in dates]
        return np.array(values), None

    columns = models[name]
    train_x = future_inputs = None
    if columns:
        mean = train[columns].mean()
        deviation = train[columns].std().replace(0, 1)
        train_x = (train[columns] - mean) / deviation
        future_inputs = (future_x[columns] - mean) / deviation

    model = SARIMAX(train["inflation"], exog=train_x, order=(1, 0, 0),
                    seasonal_order=(1, 0, 0, 12), trend="c",
                    enforce_stationarity=False, enforce_invertibility=False)
    fitted = model.fit(disp=False, maxiter=300)
    prediction = fitted.get_forecast(steps=len(dates), exog=future_inputs)
    return np.asarray(prediction.predicted_mean), fitted''')
md('''### C2. Fit using only information through each origin
For a target and horizon, the **origin** is the target minus that many months. Each fit uses inflation only through its origin. The same origin can serve several targets, so save its three predictions and reuse them rather than fit the same model again.

Record whether the numerical fit converged. Failed calculations stop execution; they are not replaced with another model's predictions. A nonconverged model is not eligible for selection.''')
code('''records = []
for phase, targets in [("Validation", validation_months), ("Test", test_months)]:
    for name in models:
        saved_forecasts = {}
        for target in targets:
            for horizon in [1, 2, 3]:
                origin = target - pd.DateOffset(months=horizon)
                if origin not in saved_forecasts:
                    train = model_data.loc[:origin]
                    dates = pd.date_range(origin + pd.offsets.MonthBegin(1), periods=3, freq="MS")
                    source_dates = dates - pd.DateOffset(months=5)
                    assert (source_dates <= origin - pd.DateOffset(months=2)).all()
                    future_x = pd.DataFrame(data.loc[source_dates, inputs].to_numpy(),
                                            index=dates, columns=lag_columns)
                    predicted, fitted = make_forecast(name, train, future_x)
                    converged = fitted is None or bool(fitted.mle_retvals["converged"])
                    saved_forecasts[origin] = (predicted, converged)
                predicted, converged = saved_forecasts[origin]
                actual = model_data.loc[target, "inflation"]
                records.append({"phase": phase, "model": name, "origin": origin,
                                "target": target, "horizon": horizon, "actual": actual,
                                "predicted": predicted[horizon - 1], "converged": converged})
        print(phase, name, "complete")

results = pd.DataFrame(records)
results["error"] = results["predicted"] - results["actual"]
assert np.isfinite(results[["predicted", "actual", "error"]]).all().all()
for phase, count in [("Validation", 12), ("Test", 24)]:
    rows = results[results["phase"] == phase]
    assert rows.groupby(["model", "horizon"]).size().eq(count).all()
    date_sets = rows.groupby(["model", "horizon"])["target"].apply(lambda dates: tuple(sorted(dates)))
    assert len(set(date_sets)) == 1, "Models must use the same target months"
display(results.head(9).round(4))''')
md('''## D. RESULTS
### D1. Calculate errors and choose on validation only
**MAE:** average absolute error. **RMSE:** square root of average squared error; large mistakes count more. Both are in percentage points and lower is better. Average the three validation RMSEs to choose one model. Do not change the choice based on the final test results.''')
code('''results["absolute_error"] = results["error"].abs()
results["squared_error"] = results["error"] ** 2
metrics = results.groupby(["phase", "model", "horizon"]).agg(
    MAE=("absolute_error", "mean"), MSE=("squared_error", "mean"), N=("error", "size")
).reset_index()
metrics["RMSE"] = np.sqrt(metrics["MSE"])
metrics = metrics[["phase", "model", "horizon", "MAE", "RMSE", "N"]]
validation = results[results["phase"] == "Validation"]
eligible = validation.groupby("model")["converged"].all()
scores = metrics[metrics["phase"] == "Validation"].groupby("model")["RMSE"].mean()
scores = scores[eligible[eligible].index].sort_values()
assert len(scores) > 0, "No converged validation model"
selected_model = scores.index[0]
display(eligible.rename("all validation fits converged").to_frame())
display(scores.rename("mean validation RMSE").to_frame().round(4))
display(metrics.round(4))
print("Validation-selected model:", selected_model)
results.to_csv(OUT / "predictions.csv", index=False)
metrics.to_csv(OUT / "metrics.csv", index=False)''')
md('''### D2. Compare model errors
The bars use identical final-test target months at each horizon. A model can win validation and still do worse than a simpler model on the test period.''')
code('''test_metrics = metrics[metrics["phase"] == "Test"]
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
for axis, measure in zip(axes, ["MAE", "RMSE"]):
    table = test_metrics.pivot(index="model", columns="horizon", values=measure).reindex(models)
    table.plot.barh(ax=axis, color=["black", "gray", "silver"])
    axis.set_title("Previously seen test: " + measure)
    axis.set_xlabel("Error (percentage points)")
    axis.set_ylabel("")
    axis.legend(title="Months ahead")
fig.tight_layout()
fig.savefig(OUT / "02_model_comparison.png")
plt.show()
plt.close(fig)

selected_metrics = test_metrics[test_metrics["model"] == selected_model]
for row in selected_metrics.itertuples():
    print(f"{selected_model}, {row.horizon} month(s): MAE {row.MAE:.3f} pp, RMSE {row.RMSE:.3f} pp.")
comparison = test_metrics.pivot(index="horizon", columns="model", values="RMSE")
display(comparison.round(4))
print("A lower error is better. These are not percentage accuracy scores.")''')
md('''### D3. Plot actual versus predicted inflation
Show the selected model at each horizon. The forecast for each target was made at an earlier origin. Look for large misses and delayed responses when inflation rises or falls quickly.''')
code('''selected_results = results[(results["phase"] == "Test") & (results["model"] == selected_model)]
fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
for axis, horizon in zip(axes, [1, 2, 3]):
    rows = selected_results[selected_results["horizon"] == horizon].sort_values("target")
    axis.plot(rows["target"], rows["actual"], color="black", label="Actual")
    axis.plot(rows["target"], rows["predicted"], color="gray", linestyle="--", label="Predicted")
    axis.set_title(f"{selected_model}: {horizon} month(s) ahead")
    axis.set_ylabel("Inflation (%)")
    axis.legend()
axes[-1].set_xlabel("Target month")
fig.tight_layout()
fig.savefig(OUT / "03_actual_vs_predicted.png")
plt.show()
plt.close(fig)''')
md('''### D4. Refit and forecast the next three months
Fit the validation-selected model through July 2026 and forecast August–October. Prepare future rows from known-earlier March–May indicators. Do not insert actual future economic values.

A basic residual check asks whether the fitted errors still have a pattern over time. If its p-value is below 0.05, keep the model provisional. Passing this one check would not prove the model is fully adequate.''')
code('''origin = model_data.index[-1]
future_dates = pd.date_range(origin + pd.offsets.MonthBegin(1), periods=3, freq="MS")
source_dates = future_dates - pd.DateOffset(months=5)
assert (source_dates <= origin - pd.DateOffset(months=2)).all()
future_x = pd.DataFrame(data.loc[source_dates, inputs].to_numpy(), index=future_dates, columns=lag_columns)
values, final_fit = make_forecast(selected_model, model_data, future_x)
forecast_table = pd.DataFrame({"target": future_dates, "forecast": values})
if final_fit is not None:
    assert final_fit.mle_retvals["converged"], "Final model did not converge"
    columns = models[selected_model]
    forecast_x = None
    if columns:
        forecast_x = (future_x[columns] - model_data[columns].mean()) / model_data[columns].std().replace(0, 1)
    prediction = final_fit.get_forecast(steps=3, exog=forecast_x)
    bounds = np.asarray(prediction.conf_int())
    forecast_table["lower_95"] = bounds[:, 0]
    forecast_table["upper_95"] = bounds[:, 1]
    residuals = final_fit.resid.iloc[max(24, int(final_fit.loglikelihood_burn)):]
    residual_check = acorr_ljungbox(residuals, lags=[12], model_df=2, return_df=True)
    display(residual_check.round(5))
    if residual_check["lb_pvalue"].iloc[0] < 0.05:
        print("Review needed: fitted errors still have a time pattern. Forecasts are provisional.")
    else:
        print("No remaining pattern detected at this check's lag; further review is still needed.")
else:
    print("Benchmark selected; fitted residual checks and intervals are not implemented for it.")
display(forecast_table.round(4))
forecast_table.to_csv(OUT / "forecast.csv", index=False)''')
code('''fig, axis = plt.subplots(figsize=(11, 4))
history = data["inflation"].iloc[-24:]
axis.plot(history.index, history, color="black", label="History through July 2026")
axis.plot([origin, *future_dates], [history.iloc[-1], *values], color="black",
          linestyle="--", marker="o", label="Forecast")
if "lower_95" in forecast_table:
    axis.fill_between(future_dates, forecast_table["lower_95"], forecast_table["upper_95"],
                      color="silver", alpha=0.5, label="Conditional 95% interval")
axis.axvline(origin, color="gray", linestyle=":")
axis.set_title("Three-month forecast: " + selected_model)
axis.set_ylabel("Inflation (%)")
axis.set_xlabel("Reference / target month")
axis.legend()
fig.tight_layout()
fig.savefig(OUT / "04_forecast.png")
plt.show()
plt.close(fig)

display(Markdown(f"**Result:** {selected_model} has the lowest average validation RMSE among the complete, converged candidates. "
    "Compare its test errors with the benchmarks and SARIMA in the table above. A variable that helps in one period may not help in another. "
    "The intervals show model-based uncertainty, not guaranteed bounds. This is an academic forecast, not an official PSA or BSP forecast."))''')
md('''### D5. What this experiment covers
- Monthly national inflation, January 2010–July 2026.
- The proposal's three core indicators, tested individually and together.
- Naive and seasonal-naive comparisons, SARIMA and SARIMAX.
- Earlier-origin validation, a separate final block, and results at 1–3 months.
- MAE/RMSE, actual-versus-predicted plots, a basic error-pattern check and forecast intervals.

**Still limited:** source files have not been independently authenticated; original release dates/data versions are missing; policy text and definition changes need review; settings are a small fixed comparison, not a full study of predictor stability. The final period was previously seen. Unemployment is absent. No dashboard or usability assessment is included in this model-only experiment.''')
dest=ROOT/'notebooks/04_proposal_simple_experiment.ipynb'
if dest.exists():raise FileExistsError('Preserve existing notebook; edit directly.')
n=nb.v4.new_notebook(cells=cells,metadata={"kernelspec":{"name":"python3","language":"python","display_name":"Python 3 (.venv)"}})
nb.write(n,dest)
print(dest)

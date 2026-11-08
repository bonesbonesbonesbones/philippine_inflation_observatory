# Philippine Inflation Observatory

A local academic prototype based on the supplied project proposal. Includes a Streamlit dashboard, two Jupyter notebooks, immutable raw datasets, prepared monthly observations, and a normalized SQL database.

## Run

Use Python 3.12. Create a virtual environment and install `requirements.txt`. Open `notebooks/01_data_preparation.ipynb` and run all cells, then do the same for `notebooks/02_model_development.ipynb`. Model fitting, chronological validation, final testing, and forecast generation are in notebook 02. The preparation parser and database loader are reusable modules.

Launch the dashboard with `python -m streamlit run app.py`. It reads the normalized database and notebook exports; it never trains models during page navigation. `tools/run_notebooks.py` runs both notebooks noninteractively using the installed Python kernel and saves their executed outputs.

`start.ps1` uses the project's `.venv` environment. Launch with PowerShell: `./start.ps1`. To regenerate all notebook outputs: `./start.ps1 -Train`.

On a new checkout, run `python -m venv .venv`, then `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`. Start the dashboard with `.\.venv\Scripts\python.exe -m streamlit run app.py`. Running `python app.py` directly does not start the Streamlit dashboard. In VS Code, select `.venv` as the interpreter and use the **Run dashboard** debug configuration.

## Data and modeling contract

The dashboard also includes DengueAware-inspired historical filters, year comparisons, and a Relationship analysis page with Pearson/Spearman correlations, 0–12 month indicator lags, scatter plots, pair counts, and filtered downloads. History, forecasts, indicators, relationships and performance include narrative interpretation. See [relationship-analysis.md](docs/relationship-analysis.md) for the descriptive analysis definitions and limitations. Historical filters do not retrain models or alter fixed evaluation periods.

Read [data-model.md](docs/data-model.md) for the ERD, grain, keys, relationships, feature timing and validation design. The schema in `database/schema.sql` is executable SQLite. SQLite supports this local prototype; migration to the proposal's MySQL environment is not yet implemented.

Primary sample: January 2010–July 2026, 199 monthly rows before growth transforms and lags. August historical inflation and other available indicators are shown separately. DCS M3 is the primary money-supply source. `ms.xls` covers December 1986–December 2005 and is excluded from the primary period. No unemployment dataset was supplied.

The source files were supplied by the user; their content has not been independently authenticated. Original publication dates and historical data vintages are absent. Backtests are retrospective with a documented assumed two-month availability delay and five-month target-relative predictor lag. Do not describe them as verified real-time accuracy. Policy text extraction, policy-regime changes, effective dates, M3 revisions, full predictor stability analysis, and SUS user testing still require research review.

Validation selects among a bounded candidate grid. Final test results use a separate 24-month block. Each horizon/model shares target months; expanding refits use only inflation observed through each origin. Model-generated conditional intervals are not guarantees. Outputs are experimental analytical estimates, not official PSA/BSP forecasts.

## Prototype checks

`python tools/check_project.py` checks monthly continuity, source hashes, database FK integrity, fact grain, forecast date arithmetic, stored errors and evaluation sample counts. Dashboard interaction is smoke-tested using Streamlit's AppTest. The two notebooks retain executed cell outputs for review.

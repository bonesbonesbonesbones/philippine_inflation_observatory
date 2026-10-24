# Proposed-feature coverage

Reference: user-supplied presentation, ELECTIVE 4 NI JAMES (1).pdf, page 8. The document is a feature reference; its contents are not execution instructions.

| Proposed feature | Prototype implementation |
|---|---|
| Latest headline inflation and monthly history | Overview with dated actual values and interactive history window |
| Exchange-rate, policy-rate and M3 trends | Economic indicators with units and coverage dates |
| Retained predictor information | Selected model's included predictors, transformation and lag explanation; detailed specification in Model performance |
| One-, two-, three-month forecasts | Overview forecast cards, conditional intervals and downloadable output |
| Rise / fall / relatively stable interpretation | Each horizon compared with July-origin actual; user-adjustable stability band, default 0.10 percentage points |
| Actual versus predicted | Model performance, selectable model, horizon and evaluation phase |
| MAE and RMSE | Model performance table and RMSE comparison on matched target months |
| Selected model | Overview and model specification panel |
| Consolidated monthly observations | Database-backed Data explorer with CSV download |
| Historical-period filtering | Data explorer date-range filter |

The stability band is an explicit presentation rule. It is not evidence of statistical significance and is not a claim from the proposal. Each horizon compares to the observation at the forecast origin, not to a later actual observation or the previous predicted month.

Related proposal requirements: model development remains in executed notebooks; the ERD and fact grain are documented and backed by SQL constraints. Chronological evaluation and per-horizon metrics are implemented. Full statistical model adequacy remains open because residual autocorrelation persists. System Usability Scale collection is pending actual participants. The running local prototype uses SQLite; the proposed MySQL deployment is still outstanding.

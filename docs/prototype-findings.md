# Prototype findings

## Dataset readiness

The uploaded inflation exports contain one Philippines all-items series, with a backcast segment through 2018 and a second segment from 2019. Both identify the 2018=100 CPI basis. The prepared primary window contains 199 consecutive months from January 2010 through July 2026. Inflation, monthly average PHP/USD, policy rate, and M3 are populated throughout that primary window.

The application also displays August 2026 where supplied. August M3 is unavailable and remains blank. Four empty future inflation cells in the 2026 export are missing values, not zero. The legacy monetary-survey workbook ends in December 2005 and is excluded from the primary sample. Unemployment was not supplied.

M3 date headers include revision/provisional suffixes. The parser handles those headers explicitly. Five 2011 policy decisions state that rates were held without repeating a numeric rate. They are exported to the review list and the previous numeric decision is carried forward. Policy effective dates and the 2016 operating-framework change need manual review before a final research experiment.

## Experiment

After M3 year-on-year growth and the fixed five-month predictor lag, the shared model sample begins June 2011. All eight candidates use the same target-month sets. Validation targets are August 2023–July 2024; final test targets are August 2024–July 2026. Each model has 12 validation targets and 24 test targets at each of the three horizons.

The combined SARIMAX candidate wins the mean validation-horizon RMSE criterion. Its final test errors are:

| Horizon | MAE (percentage points) | RMSE (percentage points) | Target months |
|---|---:|---:|---:|
| 1 month | 0.488 | 0.767 | 24 |
| 2 months | 0.785 | 1.211 | 24 |
| 3 months | 1.099 | 1.502 | 24 |

The naive benchmark has test RMSE of 0.873, 1.416, and 1.760 at the same horizons. This is evidence for the bounded comparison on the supplied vintage, not proof of general superiority or economic causality. Single-indicator ablations and both univariate candidates remain visible in the dashboard.

The selected July-origin refit generates approximately 5.94%, 5.81%, and 5.83% for August, September, and October 2026. August's supplied actual is 6.1%, shown separately. No later actual values are invented.

## Decision and remaining analysis

Use this model to demonstrate the prototype workflow, with the provisional label retained. The production fit converges but has a lag-12 Ljung–Box p-value around 0.0045, indicating remaining residual autocorrelation. This does not meet full model-adequacy review. The next research iteration should investigate residual ACF/PACF, additional training-only specifications, coefficient stability, predictor redundancy and contribution across origins, and interval coverage. Any expanded tuning should use development data and a newly reserved final assessment period rather than repeatedly optimizing against this test block.

Original release dates and historical vintages were not supplied. Predictor timing uses a fixed lag that assumes values are known within two months, and historical revisions may remain in the files. Results are retrospective, not a verified real-time backtest. The source file hashes, normalized facts and dataset snapshots preserve reproducibility of this prototype. Statistical review, source authentication, policy parsing review, and user SUS evaluation remain outstanding academic work.

## Engineering validation

Both notebooks execute with outputs and no cell errors. Checks pass for source hashes, primary monthly coverage, observation grain uniqueness, foreign keys, forecast origin/target/horizon arithmetic, stored scoring errors, and identical evaluation target sets. All five dashboard views and the model, horizon and indicator selectors pass Streamlit interaction smoke tests. The dashboard uses the populated SQLite database for observations and exported notebook artifacts for predictions and evaluation. MySQL deployment is not implemented in this local prototype.

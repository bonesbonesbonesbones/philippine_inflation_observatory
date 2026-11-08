# Historical and relationship analysis

The visual reference is the local DengueAwarePrototype's PHO dashboard: dark sidebar, blue active navigation, white bordered cards, and year/period controls. Inflation remains a monthly national series; geographic and weekly filters from DengueAware are not applicable.

Shared historical filters default to the latest 36 available months. Quick choices select the last 12 months, last 3 years, latest observed year, selected years, a custom range, or all history. Presets are relative to the latest supplied month, not today. Choose years includes all available months in each selected year independently of prior date limits. Custom calendars normalize to whole months and synchronize with a two-handle month slider. Previous/Next moves a complete window within dataset bounds. Reset all restores all 200 available months. Unfinished calendar selections keep the last complete range visible; an empty year selection prompts the user to choose years.

The selected period survives navigation through pages with no historical controls. Charts, narratives, downloads and KPI cards respond immediately. Overview cards show period-end inflation, average monthly rate, peak inflation and first-to-last change. Indicator cards show the latest available selected values with units and dates. Relationship cards show correlation, paired months, lag and paired coverage. Data explorer cards show selected rows, complete rows and missing values. Performance cards respond to the evaluation phase/horizon.

Historical filters never refit models or alter the fixed forecast origin or evaluation blocks. Forecast overlays are available only when the origin lies in the selected history; earlier windows keep their own time axis. Fixed-origin forecasts remain separately labeled.

Historical narratives summarize the first and last selected observations, their percentage-point difference, the unweighted average rate, and observed peaks/troughs. With noncontiguous year selections, those are descriptions of selected observations rather than uninterrupted trends. Rates are never summed or described as cumulative inflation.

Relationship analysis compares inflation with PHP/USD, the policy rate, M3 growth, or M3 levels. The default is monthly changes, computed on the complete calendar before filtering. First differences of percentages are percentage points; the first difference of M3 is in million PHP, not a growth rate. Pearson and Spearman are supported. Pairwise correlation requires at least three complete observations and variation in both variables; otherwise it is unavailable.

For lag k, inflation in month t is paired with the selected indicator in month t-k. The indicator month can lie before the selected target window and is included in exported paired records. Calendar alignment happens before applying filters, so missing months and skipped years do not become artificial one-month lags.

The lag comparison shows 0–12 months with paired sample counts. The correlation matrix is explicitly same-month, with pairwise counts in hover details. Its lag is always zero, independent of the single-pair lag selector. Neither view performs model selection. Searching many lags is exploratory and can find chance patterns.

Narratives distinguish association from causation and forecast contribution. Trends, autocorrelation, revisions and omitted variables can affect correlations; no independent-sample p-values or causal claims are presented. The new module contains descriptive calculations only. Model fitting remains in the existing notebooks.

Verification includes calendar-lag alignment, missing-month gaps, constant/short samples, narrative boundaries, preset counts, bounded period stepping, live KPI changes, bidirectional calendar/slider synchronization, period persistence across unrelated pages, empty year selections, reset, relationship controls, and smoke tests of all seven views.

"""Add plain-language result notes to the executed notebook without changing fits."""
from pathlib import Path
import nbformat as nb
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'notebooks/04_proposal_simple_experiment.ipynb'
n=nb.read(path,as_version=4)
for cell in n.cells:
    if cell.cell_type=='code' and 'selected_model = scores.index[0]' in cell.source:
        cell.source=cell.source.replace('display(eligible.rename(',
            'display(results.groupby(["phase", "model"])["converged"].agg(["count", "sum"]).rename(columns={"count": "forecasts", "sum": "forecasts from converged fits"}))\ndisplay(eligible.rename(')
    if cell.cell_type=='markdown' and '### D2.' in cell.source:
        cell.source+='\n\n**Check the fit-status table too.** Test errors below include any forecasts marked `converged=False` so the dates stay the same for every model. Those numerical fits need review; their scores are provisional, not fully verified results. Validation selection allows only models whose validation fits all converged.'
metrics=pd.read_csv(ROOT/'artifacts/proposal_simple_experiment/metrics.csv')
r=pd.read_csv(ROOT/'artifacts/proposal_simple_experiment/predictions.csv')
failed=r.loc[~r.converged,['phase','model','origin']].drop_duplicates()
text='''### D6. Plain-language result review
The combined SARIMAX was selected using validation errors only. Its reported final-test RMSE is **0.767, 1.211 and 1.502 percentage points** at 1, 2 and 3 months, compared with SARIMA **0.776, 1.246 and 1.560**. These differences are small; they do not prove that all three indicators always improve forecasts.

**Important:** the combined model did not converge at the August 2024 origin. This affects three of its 72 final-test forecasts. Its full test score includes those records and must be treated as provisional. The final July 2026 fit converged, but its residual check still found a time pattern. Keep both limitations when presenting the results.

Other test fits needing review:
'''
for row in failed.itertuples(index=False):text+=f'- {row.model}: origin {row.origin}.\n'
text+='\nNo model was switched or retuned after seeing these test results. Earlier notebooks and application artifacts were not changed.'
if not any('### D6.' in c.source for c in n.cells):n.cells.append(nb.v4.new_markdown_cell(text))
nb.write(n,path)
print('Added fit-status counts and result interpretation.')

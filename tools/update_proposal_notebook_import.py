from pathlib import Path
import nbformat as nb
path=Path(__file__).resolve().parents[1]/'notebooks/04_proposal_simple_experiment.ipynb'
n=nb.read(path,as_version=4)
for cell in n.cells:
    if cell.cell_type=='code':
        cell.source=cell.source.replace('from pathlib import Path\n','from pathlib import Path\nfrom datetime import datetime\n')
        cell.source=cell.source.replace('__import__("datetime").datetime','datetime')
nb.write(n,path)

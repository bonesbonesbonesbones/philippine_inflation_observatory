"""Execute notebooks via a local kernel and retain cell outputs for review."""
from pathlib import Path
import os
import sys
ROOT = Path(__file__).resolve().parents[1]
os.environ['JUPYTER_RUNTIME_DIR']=str(ROOT/'.jupyter/runtime')
os.environ['IPYTHONDIR']=str(ROOT/'.jupyter/ipython')
Path(os.environ['JUPYTER_RUNTIME_DIR']).mkdir(parents=True,exist_ok=True)
if sys.prefix == sys.base_prefix and (ROOT/'.packages').exists():
    sys.path.insert(0,str(ROOT/'.packages'))
import nbformat
from nbclient import NotebookClient
from jupyter_client.kernelspec import KernelSpecManager

kernel_root = ROOT/'.jupyter/kernels'
kernel = kernel_root/'elec4'
kernel.mkdir(parents=True,exist_ok=True)
(kernel/'kernel.json').write_text(__import__('json').dumps({
    'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],
    'display_name':'ELEC4 local Python','language':'python',
    'env':{'PYTHONPATH':str(ROOT) if sys.prefix != sys.base_prefix else str(ROOT/'.packages')+os.pathsep+str(ROOT),
           'PYTHONIOENCODING':'utf-8','MPLCONFIGDIR':str(ROOT/'.jupyter/matplotlib')}}))
manager = KernelSpecManager(kernel_dirs=[str(kernel_root)])
paths = [ROOT/'notebooks'/name for name in sys.argv[1:]] if len(sys.argv)>1 else sorted((ROOT/'notebooks').glob('*.ipynb'))
for path in paths:
    print('Executing',path.name,flush=True)
    notebook = nbformat.read(path,as_version=4)
    client = NotebookClient(notebook,timeout=1800,kernel_name='elec4',resources={'metadata':{'path':str(ROOT)}})
    client.km = __import__('jupyter_client').KernelManager(kernel_name='elec4',kernel_spec_manager=manager)
    try:
        client.execute()
    finally:
        nbformat.write(notebook,path)
    print('Saved executed',path.name,flush=True)

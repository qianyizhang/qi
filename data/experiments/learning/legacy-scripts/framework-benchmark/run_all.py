import subprocess
from pathlib import Path
import random
root=Path(__file__).resolve().parent
repo=root.parents[2]
old=repo/'.venv/bin/python'
new=root/'venv/bin/python'
jobs=[]
for batch in (96,768):
    for tag,python,backend,device,threads in [('torch210-mps',old,'torch','mps',1),('torch214-mps',new,'torch','mps',1),('mlx',new,'mlx','gpu',1),('mlx-compiled',new,'mlx-compiled','gpu',1),('torch214-cpu6',new,'torch','cpu',6)]:
        jobs.append((tag,python,backend,device,threads,batch))
random.Random(207).shuffle(jobs)
for tag,python,backend,device,threads,batch in jobs:
    name=f'{tag}-{batch}'
    print('START',name,flush=True)
    cmd=[str(python),str(root/'compare.py'),'--backend',backend,'--device',device,'--threads',str(threads),'--batch',str(batch),'--output',str(root/f'{name}.json')]
    with (root/f'{name}.log').open('w') as log:
        result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=90)
    print('DONE',name,result.returncode,flush=True)
    if result.returncode: raise SystemExit((root/f'{name}.log').read_text())

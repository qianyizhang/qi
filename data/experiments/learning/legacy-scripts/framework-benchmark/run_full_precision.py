import os
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
env=dict(os.environ,MLX_ENABLE_TF32='0')
for backend,batch in [('mlx-compiled',768),('mlx',96),('mlx',768),('mlx-compiled',96)]:
    name=f'{backend}-fp32-{batch}'
    cmd=[str(root/'venv/bin/python'),str(root/'compare.py'),'--backend',backend,'--device','gpu','--batch',str(batch),'--output',str(root/f'{name}.json')]
    with (root/f'{name}.log').open('w') as log:
        subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,check=True,timeout=90)
    print('DONE',name,flush=True)

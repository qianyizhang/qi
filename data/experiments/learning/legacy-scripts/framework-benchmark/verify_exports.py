import json
from pathlib import Path
import numpy as np
import torch
root=Path(__file__).resolve().parent
inputs=np.load(root/'inputs.npz')
torch.set_num_threads(1)
rows=[]
for path in sorted(root.glob('*-96.npz'))+sorted(root.glob('*-768.npz')):
    weights=np.load(path)
    model=torch.nn.Sequential(torch.nn.Linear(1261,64),torch.nn.ReLU(),torch.nn.Linear(64,8100))
    model.load_state_dict({k:torch.from_numpy(weights[k].copy()) for k in model.state_dict()})
    result={'artifact':path.name}
    for split in ('train','validation'):
        prefix='' if split=='train' else 'v'
        x=inputs[prefix+'x']; mask=inputs[prefix+'mask']
        with torch.inference_mode():
            pred=model(torch.from_numpy(x)).masked_fill(~torch.from_numpy(mask),float('-inf')).argmax(-1).numpy()
        saved=weights[split+'_predictions'][:len(pred)]
        result[split+'_cpu_prediction_matches']=int((pred==saved).sum())
        result[split+'_positions']=len(pred)
        assert np.array_equal(pred,saved),result
    rows.append(result)
(root/'export-verification.json').write_text(json.dumps(rows,indent=2)+'\n')
print('CPU prediction transfer checks passed:',len(rows),'final parameter sets')

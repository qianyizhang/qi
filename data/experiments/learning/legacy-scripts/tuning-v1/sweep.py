"""Exploratory tuning; the previous validation split is explicitly tuning data."""
import json
import time
from pathlib import Path
from hashlib import sha256
from statistics import mean
import torch
from qi.learning.data import Dataset
from qi.learning.train import tensors, synchronize, validate_device
root=Path(__file__).resolve().parent
repo=root.parents[2]
data=Dataset.model_validate_json((repo/'artifacts/learning/generalization-v1-data.json').read_text())
validate_device('mps',1);torch.set_num_threads(1)
x,mask,y=(v.to('mps') for v in tensors(data.split_labels('train')))
vx,vmask,vy=(v.to('mps') for v in tensors(data.split_labels('validation')))
configs=[
 dict(id='baseline',width=64,lr=.01,decay=0.,smooth=0.),
 dict(id='slower',width=64,lr=.003,decay=0.,smooth=0.),
 dict(id='decay',width=64,lr=.003,decay=.01,smooth=0.),
 dict(id='smooth',width=64,lr=.003,decay=0.,smooth=.1),
 dict(id='regularized',width=64,lr=.003,decay=.01,smooth=.1),
 dict(id='wide128',width=128,lr=.003,decay=.01,smooth=.1),
 dict(id='wide256',width=256,lr=.003,decay=.01,smooth=.1),
]
manifest=dict(dataset_sha256=data.digest,script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),torch=torch.__version__,device='mps',seeds=[7,17,27],checkpoints=[50,200,800],configs=configs,split_role='768 train / 251 tuning; no untouched final test yet')
(root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
results=[];deadline=time.perf_counter()+600
for cfg in configs:
 for seed in manifest['seeds']:
    torch.manual_seed(seed)
    model=torch.nn.Sequential(torch.nn.Linear(1261,cfg['width']),torch.nn.ReLU(),torch.nn.Linear(cfg['width'],8100)).to('mps')
    optimizer=torch.optim.Adam(model.parameters(),lr=cfg['lr'],weight_decay=cfg['decay'])
    synchronize('mps');start=time.perf_counter();opt_seconds=0.
    for step in range(1,801):
        if time.perf_counter()>deadline: raise RuntimeError('Sweep reached 600-second deadline')
        optimizer.zero_grad()
        logits=model(x).masked_fill(~mask,float('-inf'))
        nll=torch.nn.functional.cross_entropy(logits,y)
        if cfg['smooth']:
            logp=torch.log_softmax(logits,dim=-1)
            smooth=-(logp.masked_fill(~mask,0.).sum(-1)/mask.sum(-1)).mean()
            loss=(1-cfg['smooth'])*nll+cfg['smooth']*smooth
        else: loss=nll
        if not torch.isfinite(loss): raise RuntimeError('Nonfinite objective')
        loss.backward();optimizer.step()
        if step in manifest['checkpoints']:
            synchronize('mps');opt_seconds+=time.perf_counter()-start
            with torch.inference_mode():
                metrics={}
                for split,xx,mm,yy in [('train',x,mask,y),('tuning',vx,vmask,vy)]:
                    output=model(xx).masked_fill(~mm,float('-inf'))
                    predictions=output.argmax(-1)
                    metrics[split]=dict(positions=len(yy),correct=int((predictions==yy).sum()),agreement=float((predictions==yy).float().mean()),cross_entropy=float(torch.nn.functional.cross_entropy(output,yy)))
                weights={k:v.cpu() for k,v in model.state_dict().items()}
            path=root/f"{cfg['id']}-seed-{seed}-step-{step}.pt"
            torch.save(dict(config=cfg,seed=seed,steps=step,dataset_sha256=data.digest,state_dict=weights),path)
            row=dict(config=cfg['id'],seed=seed,steps=step,optimization_seconds=opt_seconds,checkpoint=path.name,checkpoint_sha256=sha256(path.read_bytes()).hexdigest(),**metrics)
            results.append(row)
            (root/'results.json').write_text(json.dumps(results,indent=2)+'\n')
            print(json.dumps(row),flush=True)
            synchronize('mps');start=time.perf_counter()
summary=[]
for cfg in configs:
 for steps in manifest['checkpoints']:
    rows=[r for r in results if r['config']==cfg['id'] and r['steps']==steps]
    summary.append(dict(config=cfg['id'],steps=steps,tuning_agreement=mean(r['tuning']['agreement'] for r in rows),tuning_loss=mean(r['tuning']['cross_entropy'] for r in rows),train_agreement=mean(r['train']['agreement'] for r in rows),optimization_seconds=mean(r['optimization_seconds'] for r in rows)))
summary.sort(key=lambda r:(-r['tuning_agreement'],r['tuning_loss']))
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('SUMMARY',json.dumps(summary),flush=True)

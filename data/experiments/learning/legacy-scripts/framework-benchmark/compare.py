"""Matched local policy benchmark, isolated from production code and checkpoints."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import time
import numpy as np

p=argparse.ArgumentParser()
p.add_argument('--backend',choices=['torch','mlx','mlx-compiled'],required=True)
p.add_argument('--device',default='mps')
p.add_argument('--threads',type=int,default=1)
p.add_argument('--batch',type=int,required=True)
p.add_argument('--output',required=True)
a=p.parse_args()
root=Path(__file__).resolve().parent
arrays=np.load(root/'inputs.npz')
keys=['0.weight','0.bias','2.weight','2.bias']
weights={k:arrays['w_'+k] for k in keys}
mult=a.batch//96
x=np.tile(arrays['x'],(mult,1)); mask=np.tile(arrays['mask'],(mult,1)); y=np.tile(arrays['y'],mult)

if a.backend=='torch':
    import torch
    assert os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK')!='1'
    torch.set_num_threads(a.threads)
    if a.device=='mps': assert torch.backends.mps.is_available()
    version=torch.__version__
    def sync():
        if a.device=='mps': torch.mps.synchronize()
    def build():
        model=torch.nn.Sequential(torch.nn.Linear(1261,64),torch.nn.ReLU(),torch.nn.Linear(64,8100))
        model.load_state_dict({k:torch.from_numpy(v.copy()) for k,v in weights.items()})
        model.to(a.device)
        opt=torch.optim.Adam(model.parameters(),lr=.01,betas=(.9,.999),eps=1e-8,weight_decay=0)
        tx,tm,ty=(torch.from_numpy(v).to(a.device) for v in (x,mask,y))
        return model,opt,tx,tm,ty
    def step(state):
        model,opt,tx,tm,ty=state
        opt.zero_grad()
        loss=torch.nn.functional.cross_entropy(model(tx).masked_fill(~tm,float('-inf')),ty)
        if not torch.isfinite(loss): raise RuntimeError('Nonfinite loss')
        loss.backward(); opt.step()
        return loss
    def export(state): return {k:v.detach().cpu().numpy() for k,v in state[0].state_dict().items()}
    def evaluate(state,xx,mm,yy):
        with torch.inference_mode():
            logits=state[0](torch.from_numpy(xx).to(a.device)).masked_fill(~torch.from_numpy(mm).to(a.device),float('-inf'))
            loss=float(torch.nn.functional.cross_entropy(logits,torch.from_numpy(yy).to(a.device)))
            pred=logits.argmax(-1).cpu().numpy()
        return loss,pred
    # Warm kernels, then reset to exactly the same initial state for each trial.
    warm=build(); sync(); start=time.perf_counter()
    for _ in range(10): step(warm)
    sync(); warmup=time.perf_counter()-start
    def trial():
        state=build(); sync(); start=time.perf_counter()
        for i in range(200):
            loss=step(state)
            if i==0: initial=float(loss.detach())
        sync(); seconds=time.perf_counter()-start
        return state,seconds,initial
else:
    import mlx.core as mx
    import mlx.nn as nn
    import mlx.optimizers as optim
    from mlx.utils import tree_map,tree_flatten
    from importlib.metadata import version as package_version
    version=package_version('mlx')
    assert mx.metal.is_available()
    mx.set_default_device(mx.gpu)
    sync=mx.synchronize
    model=nn.Sequential(nn.Linear(1261,64),nn.ReLU(),nn.Linear(64,8100))
    model.load_weights([('layers.'+k,mx.array(v)) for k,v in weights.items()])
    optimizer=optim.Adam(learning_rate=.01,betas=[.9,.999],eps=1e-8,bias_correction=True)
    optimizer.init(model.trainable_parameters())
    init_params=tree_map(lambda v:v,model.parameters())
    init_opt=tree_map(lambda v:v,optimizer.state)
    mx.eval(init_params,init_opt)
    tx,tm,ty=mx.array(x),mx.array(mask),mx.array(y.astype(np.int32))
    mx.eval(tx,tm,ty)
    def loss_fn(model,xx,mm,yy):
        return nn.losses.cross_entropy(mx.where(mm,model(xx),-mx.inf),yy,reduction='mean')
    value_grad=nn.value_and_grad(model,loss_fn)
    def update(params,opt_state,xx,mm,yy):
        model.update(params); optimizer.state=opt_state
        loss,grads=value_grad(model,xx,mm,yy)
        optimizer.update(model,grads)
        return model.parameters(),optimizer.state,loss
    update=mx.compile(update) if a.backend=='mlx-compiled' else update
    def step(state):
        params,opt_state=state
        params,opt_state,loss=update(params,opt_state,tx,tm,ty)
        # Materialize every update; keep the production per-step finite check.
        mx.eval(params,opt_state,loss)
        if not mx.isfinite(loss).item(): raise RuntimeError('Nonfinite loss')
        return (params,opt_state),loss
    def export(state):
        return {k.removeprefix('layers.'):np.array(v) for k,v in tree_flatten(state[0])}
    def evaluate(state,xx,mm,yy):
        model.update(state[0])
        logits=mx.where(mx.array(mm),model(mx.array(xx)),-mx.inf)
        loss=nn.losses.cross_entropy(logits,mx.array(yy.astype(np.int32)),reduction='mean')
        pred=mx.argmax(logits,axis=-1)
        mx.eval(loss,pred)
        return float(loss),np.array(pred)
    state=(init_params,init_opt); sync(); start=time.perf_counter()
    for _ in range(10): state,_=step(state)
    sync(); warmup=time.perf_counter()-start
    def trial():
        state=(tree_map(lambda v:v,init_params),tree_map(lambda v:v,init_opt))
        sync(); start=time.perf_counter()
        for i in range(200):
            state,loss=step(state)
            if i==0: initial=float(loss)
        sync(); seconds=time.perf_counter()-start
        return state,seconds,initial

trials=[]
for repeat in range(3):
    state,seconds,initial=trial()
    final,train_pred=evaluate(state,x,mask,y)
    vl,vpred=evaluate(state,arrays['vx'],arrays['vmask'],arrays['vy'])
    trials.append(dict(seconds=seconds,initial_loss=initial,final_loss=final,validation_loss=vl,
                       train_correct=int((train_pred==y).sum()),validation_correct=int((vpred==arrays['vy']).sum()),
                       legal_train=bool(mask[np.arange(len(y)),train_pred].all()),
                       legal_validation=bool(arrays['vmask'][np.arange(32),vpred].all())))
    print(json.dumps(trials[-1]),flush=True)
output=Path(a.output)
np.savez(output.with_suffix('.npz'),**export(state),train_predictions=train_pred,validation_predictions=vpred)
result=dict(backend=a.backend,device=a.device,threads=a.threads,version=version,batch=a.batch,steps=200,repeats=3,
            warmup_seconds=warmup,trials=trials,median_seconds=statistics.median(t['seconds'] for t in trials),
            script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            input_sha256=hashlib.sha256((root/'inputs.npz').read_bytes()).hexdigest())
output.write_text(json.dumps(result,indent=2)+'\n')
print('RESULT',json.dumps({k:v for k,v in result.items() if k!='trials'}),flush=True)

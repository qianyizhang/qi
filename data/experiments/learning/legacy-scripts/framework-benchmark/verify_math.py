"""Check ported objective, gradients, and first Adam update against CPU PyTorch."""
import json
from pathlib import Path
import numpy as np
import torch
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx.utils import tree_flatten
root=Path(__file__).resolve().parent
d=np.load(root/'inputs.npz')
torch.set_num_threads(1)
mx.set_default_device(mx.gpu)
keys=['0.weight','0.bias','2.weight','2.bias']
tm=torch.nn.Sequential(torch.nn.Linear(1261,64),torch.nn.ReLU(),torch.nn.Linear(64,8100))
tm.load_state_dict({k:torch.from_numpy(d['w_'+k].copy()) for k in keys})
mm=nn.Sequential(nn.Linear(1261,64),nn.ReLU(),nn.Linear(64,8100))
mm.load_weights([('layers.'+k,mx.array(d['w_'+k])) for k in keys])
x,mask,y=torch.from_numpy(d['x']),torch.from_numpy(d['mask']),torch.from_numpy(d['y'])
tl=tm(x)
tloss=torch.nn.functional.cross_entropy(tl.masked_fill(~mask,float('-inf')),y)
tloss.backward()
mx_x,mx_mask,mx_y=mx.array(d['x']),mx.array(d['mask']),mx.array(d['y'].astype(np.int32))
def fn(model): return nn.losses.cross_entropy(mx.where(mx_mask,model(mx_x),-mx.inf),mx_y,reduction='mean')
mloss,mg=nn.value_and_grad(mm,fn)(mm)
ml=mm(mx_x)
mx.eval(mloss,mg,ml)
checks=[]
def compare(name,left,right,atol=1e-5,rtol=1e-4):
    ok=bool(np.allclose(left,right,atol=atol,rtol=rtol))
    checks.append(dict(name=name,passed=ok,max_absolute_error=float(np.max(np.abs(left-right))),atol=atol,rtol=rtol))
    assert ok,checks[-1]
compare('initial_logits',tl.detach().numpy(),np.array(ml))
compare('initial_loss',np.array(float(tloss.detach())),np.array(float(mloss)))
for k,g in tree_flatten(mg):
    compare('gradient_'+k,dict(tm.named_parameters())[k.removeprefix('layers.')].grad.numpy(),np.array(g))
to=torch.optim.Adam(tm.parameters(),lr=.01,betas=(.9,.999),eps=1e-8)
mo=optim.Adam(learning_rate=.01,betas=[.9,.999],eps=1e-8,bias_correction=True)
to.step(); mo.update(mm,mg); mx.eval(mm.parameters(),mo.state)
for k,v in tree_flatten(mm.parameters()):
    compare('first_update_'+k,tm.state_dict()[k.removeprefix('layers.')].numpy(),np.array(v))
(root/'math-verification.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks,indent=2))

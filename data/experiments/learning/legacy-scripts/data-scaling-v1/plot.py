import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root=Path(__file__).resolve().parent
verified=json.loads((root/'verification.json').read_text())
summary=json.loads((root/'curve-cached/summary.json').read_text())
rows=verified['curve']
sizes=np.array([r['size'] for r in rows])
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,2,figsize=(10,4.2),layout='constrained')
for split,color,label in [('train','#87909c','Training'),('validation','#1565c0','Held-out games')]:
    values=np.array([r[f'{split}_agreement_mean'] for r in rows])*100
    sd=np.array([r[f'{split}_agreement_std'] for r in rows])*100
    axes[0].plot(sizes,values,'o-',color=color,label=label,lw=2)
    axes[0].fill_between(sizes,values-sd,values+sd,color=color,alpha=.15)
    if split=='validation':
        for x,y in zip(sizes,values): axes[0].annotate(f'{y:.1f}%',(x,y),xytext=(0,10),textcoords='offset points',ha='center',color=color)
chance=summary['curve'][0]['random_legal_agreement']*100
axes[0].axhline(chance,color='#ad7d21',ls=':',label='Random legal move')
axes[0].set(ylabel='Exact teacher agreement (%)',ylim=(0,105),title='Does more data improve imitation?')
axes[0].legend(loc='upper left',bbox_to_anchor=(0,.89),frameon=False,fontsize=9)
for split,color,label in [('train','#87909c','Training'),('validation','#1565c0','Held-out games')]:
    values=np.array([r[f'{split}_cross_entropy_mean'] for r in rows])
    axes[1].plot(sizes,values,'o-',color=color,label=label,lw=2)
axes[1].set(ylabel='Cross-entropy (lower is better)',title='Does prediction loss decrease?',ylim=(0,None))
for ax in axes:
    ax.set_xscale('log',base=4)
    ax.set_xticks(sizes,[f'{n:,}' for n in sizes])
    ax.set_xlabel('Unique training positions')
    ax.grid(axis='y',alpha=.15)
fig.suptitle('Same small policy, 16× more training data',fontsize=16,weight='bold')
fig.supxlabel(f"Fixed {verified['validation_positions']:,}-position holdout · three seeds · 200 full-batch Adam updates\nShading: seed standard deviation. Imitation accuracy does not establish playing strength.",fontsize=9)
fig.savefig(root/'learning-curve.png',dpi=160)
fig.savefig(root/'learning-curve.svg')

"""Independent CPU recomputation and source-game paired bootstrap for the locked curve."""
import json
import math
from pathlib import Path
from statistics import mean, pstdev
import numpy as np
import torch
from qi.evaluation import Corpus
from qi.learning.data import Dataset
from qi.learning.experiment import ordered_inputs
from qi.learning.train import tensors
from qi.players.policy.encoding import action_id
from qi.players.policy.runtime import load_checkpoint

root=Path(__file__).resolve().parent
run=root/'curve-cached'
data=Dataset.model_validate_json((run/'dataset.json').read_text())
manifest=json.loads((run/'manifest.json').read_text())
summary=json.loads((run/'summary.json').read_text())
selection=json.loads((root/'selection.json').read_text())
assert data.digest==manifest['dataset_sha256']
assert data.reserved_corpus.digest==Corpus.model_validate_json(Path('data/evaluation/search-positions-v1.json').read_text()).digest
assert summary['status']=='complete' and len(summary['trials'])==9
assert {(t['size'],t['seed']) for t in summary['trials']}=={(n,s) for n in selection['sizes'] for s in selection['seeds']}
assert manifest['ordered_train_inputs']==ordered_inputs(data,selection['subset_seed'])
old=set()
for path in json.loads((root/'preparation.json').read_text())['excluded_files']:
    old.update(r['input_sha256'] for r in json.loads(Path(path).read_text())['labels'])
assert not old.intersection(r.input_sha256 for r in data.labels)
train={r.input_sha256:r for r in data.split_labels('train')}
validation=data.split_labels('validation')
assert manifest['validation_inputs']==[r.input_sha256 for r in validation]
all_games={r.input_sha256:r.analysis.snapshot.game() for r in data.labels}
validation_games=[all_games[r.input_sha256] for r in validation]
val_tensors=tensors(validation,validation_games)
torch.set_num_threads(1)

def evaluate(model, values):
    features,mask,targets=values
    losses=[]
    predictions=[]
    with torch.inference_mode():
        for start in range(0,len(targets),128):
            logits=model(features[start:start+128]).masked_fill(~mask[start:start+128],-torch.inf)
            losses.extend(torch.nn.functional.cross_entropy(logits,targets[start:start+128],reduction='none').tolist())
            predictions.extend(logits.argmax(dim=1).tolist())
    assert all(math.isfinite(v) for v in losses)
    correct=np.array(predictions)==targets.numpy()
    return dict(agreement=float(correct.mean()),cross_entropy=mean(losses)),correct,predictions

verified=[]
train_tensor_cache={}
for trial in summary['trials']:
    size,seed,report=trial['size'],trial['seed'],trial['report']
    assert size in selection['sizes'] and seed in selection['seeds']
    policy=load_checkpoint(str((run/f'size-{size}-seed-{seed}.pt').resolve()))
    md=policy.metadata
    assert policy.sha256==report['checkpoint_sha256']
    assert md.dataset_sha256==data.digest
    assert md.seed==seed and md.steps==selection['steps'] and md.learning_rate==selection['learning_rate']
    assert md.train_inputs==manifest['ordered_train_inputs'][:size]
    assert md.validation_inputs==manifest['validation_inputs']
    val_stats,correct,predictions=evaluate(policy.model,val_tensors)
    assert predictions==[action_id(policy.predict(game)) for game in validation_games]
    if size not in train_tensor_cache:
        train_tensor_cache[size]=tensors([train[key] for key in md.train_inputs],[all_games[key] for key in md.train_inputs])
    train_stats,_,_=evaluate(policy.model,train_tensor_cache[size])
    for split,stats in [('train',train_stats),('validation',val_stats)]:
        for key,value in stats.items():
            assert abs(value-report[split][key])<1e-5,(size,seed,split,key,value,report[split][key])
    verified.append(dict(size=size,seed=seed,checkpoint_sha256=policy.sha256,train=train_stats,validation=val_stats,correct=correct.astype(int).tolist()))
    print(json.dumps(dict(verified_size=size,seed=seed,validation=val_stats)),flush=True)

curve=[]
for size in selection['sizes']:
    rows=[r for r in verified if r['size']==size]
    assert len(rows)==len(selection['seeds'])
    row=dict(size=size)
    for split in ['train','validation']:
        for metric in ['agreement','cross_entropy']:
            values=[r[split][metric] for r in rows]
            row[f'{split}_{metric}_mean']=mean(values)
            row[f'{split}_{metric}_std']=pstdev(values)
    reported=next(r for r in summary['curve'] if r['size']==size)
    for key,value in row.items():
        assert abs(value-reported[key])<1e-5
    curve.append(row)

source_ids=sorted({r.source_id for r in validation})
source_index={source:index for index,source in enumerate(source_ids)}
groups=np.array([source_index[r.source_id] for r in validation])
counts=np.bincount(groups,minlength=len(source_ids))
base=np.mean([r['correct'] for r in verified if r['size']==selection['sizes'][0]],axis=0)
rng=np.random.default_rng(211)
draws=rng.integers(0,len(source_ids),size=(5000,len(source_ids)))
comparisons=[]
for size in selection['sizes'][1:]:
    candidate=np.mean([r['correct'] for r in verified if r['size']==size],axis=0)
    delta=np.bincount(groups,weights=candidate-base,minlength=len(source_ids))
    draws_delta=delta[draws].sum(axis=1)/counts[draws].sum(axis=1)
    comparisons.append(dict(size=size,baseline_size=selection['sizes'][0],gain_percentage_points=float((candidate-base).mean()*100),paired_source_bootstrap_95_percentile_interval=(np.quantile(draws_delta,[.025,.975])*100).tolist()))
equivalence=[]
old_summary=json.loads((root/'curve/summary.json').read_text())
assert old_summary['status']=='interrupted'
for trial in old_summary['trials']:
    name=f"size-{trial['size']}-seed-{trial['seed']}.pt"
    old_policy=load_checkpoint(str((root/'curve'/name).resolve()))
    new_policy=load_checkpoint(str((run/name).resolve()))
    assert old_policy.metadata==new_policy.metadata
    assert all(torch.equal(old_policy.model.state_dict()[key],value) for key,value in new_policy.model.state_dict().items())
    equivalence.append(dict(size=trial['size'],seed=trial['seed'],weights_bit_identical=True))
result=dict(replay_optimization_equivalence=equivalence,status='verified',dataset_sha256=data.digest,validation_positions=len(validation),validation_games=len(source_ids),curve=curve,comparisons=comparisons,bootstrap=dict(draws=5000,seed=211,unit='source_game',scope='Fixed dataset and three-seed average; does not cover training-data or teacher uncertainty.'),trials=verified)
(root/'verification.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
print(json.dumps(dict(status='verified',curve=curve,comparisons=comparisons)),flush=True)

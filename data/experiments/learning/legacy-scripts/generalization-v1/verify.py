"""Recompute saved learning-curve evidence from dataset and CPU checkpoints."""
import json
import math
from pathlib import Path
from hashlib import sha256
from statistics import mean, pstdev
import torch
from qi.learning.data import Dataset, reserved_inputs
from qi.players.policy.runtime import load_checkpoint
from qi.players.policy.encoding import action_id, encode
from qi.game import legal_moves
root=Path(__file__).resolve().parent
manifest=json.loads((root/'manifest.json').read_text())
summary=json.loads((root/'summary.json').read_text())
data=Dataset.model_validate_json((root/'dataset.json').read_text())
assert manifest['dataset_sha256']==data.digest
assert manifest['reserved_corpus_sha256']==data.reserved_corpus.digest
reserved=reserved_inputs(data.reserved_corpus)
assert not {l.input_sha256 for l in data.labels}&reserved
labels={l.input_sha256:l for l in data.labels}
validation=data.split_labels('validation')
seen=set(); recomputed=[]
for trial in summary['trials']:
    size,seed,report=trial['size'],trial['seed'],trial['report']
    assert (size,seed) not in seen; seen.add((size,seed))
    path=root/f'size-{size}-seed-{seed}.pt'
    assert report==json.loads(path.with_suffix('.json').read_text())
    assert report['checkpoint_sha256']==sha256(path.read_bytes()).hexdigest()
    policy=load_checkpoint(str(path))
    meta=policy.metadata
    assert meta.train_inputs==manifest['ordered_train_inputs'][:size]
    assert meta.validation_inputs==manifest['validation_inputs']
    assert meta.dataset_sha256==data.digest and meta.seed==seed and meta.steps==200
    assert meta.training_device=='mps' and meta.torch_version=='2.10.0'
    assert report['completed_steps']==report['requested_steps']==200 and report['status']=='complete'
    stats={}
    for split,selected in [('train',[labels[k] for k in meta.train_inputs]),('validation',validation)]:
        correct=0; loss=[]; chance=[]; random_loss=[]
        for label in selected:
            game=label.analysis.snapshot.game()
            legal=legal_moves(game.board,game.turn)
            chosen=policy.predict(game)
            assert chosen in legal
            correct+=chosen==label.analysis.move
            ids=[action_id(move) for move in legal]
            with torch.inference_mode():
                logits=policy.model(torch.tensor([encode(game)]))[0,ids]
                logp=torch.log_softmax(logits,dim=0)
                loss.append(-float(logp[ids.index(action_id(label.analysis.move))]))
            chance.append(1/len(legal));random_loss.append(math.log(len(legal)))
        stats[split]={'correct':correct,'positions':len(selected),'agreement':correct/len(selected),'cross_entropy':mean(loss),'random_legal_agreement':mean(chance),'random_legal_cross_entropy':mean(random_loss)}
        for metric in ('agreement','cross_entropy','random_legal_agreement'):
            assert math.isclose(stats[split][metric],report[split][metric],rel_tol=1e-4,abs_tol=1e-6),(size,seed,split,metric)
    recomputed.append({'size':size,'seed':seed,**stats})
assert seen=={(size,seed) for size in manifest['plan']['sizes'] for seed in manifest['plan']['seeds']}
assert summary['status']=='complete' and len(seen)==12
for row in summary['curve']:
    group=[r for r in recomputed if r['size']==row['size']]
    for split in ('train','validation'):
        for metric in ('agreement','cross_entropy'):
            values=[r[split][metric] for r in group]
            assert math.isclose(mean(values),row[f'{split}_{metric}_mean'],rel_tol=1e-4,abs_tol=1e-6)
            assert math.isclose(pstdev(values),row[f'{split}_{metric}_std'],rel_tol=1e-3,abs_tol=1e-6)
verification={'status':'verified','trials':recomputed,'dataset_sha256':data.digest,'source_sha256':manifest['source_sha256']}
(root/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
print('Verified 12 checkpoints and all split identities, actions, losses, and curve aggregates.')
print('Random legal validation cross entropy:',recomputed[0]['validation']['random_legal_cross_entropy'])
print('Per-seed held-out correct counts:',[(r['size'],r['seed'],r['validation']['correct']) for r in recomputed])

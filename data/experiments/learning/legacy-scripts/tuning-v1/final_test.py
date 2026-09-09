"""Evaluate locked candidates once on fresh, disjoint teacher-labeled games."""
import json
from pathlib import Path
from collections import Counter
from hashlib import sha256
from statistics import mean,pstdev
import torch
from qi.learning.data import Dataset,teacher_identity
from qi.learning.train import tensors
root=Path(__file__).resolve().parent
repo=root.parents[2]
selection=json.loads((root/'selection.json').read_text())
old=Dataset.model_validate_json((repo/'artifacts/learning/generalization-v1-data.json').read_text())
fresh=Dataset.model_validate_json((root/'fresh-test-data.json').read_text())
assert fresh.reserved_corpus.digest==old.reserved_corpus.digest
assert teacher_identity(fresh.labels[0].analysis)==teacher_identity(old.labels[0].analysis)
seen={l.input_sha256 for l in old.labels}
assert not {s.snapshot.game().state_hash for s in old.sources}&{s.snapshot.game().state_hash for s in fresh.sources}
labels=[l for l in fresh.labels if l.input_sha256 not in seen]
x,mask,y=tensors(labels)
torch.set_num_threads(1)
rows=[]
for cfg in selection['candidates']:
 for seed in selection['seeds']:
    path=root/f"{cfg['id']}-seed-{seed}-step-{cfg['steps']}.pt"
    payload=torch.load(path,weights_only=True)
    assert payload['dataset_sha256']==old.digest
    assert payload['seed']==seed and payload['steps']==cfg['steps']
    assert all(payload['config'][key]==cfg[key] for key in ('width','lr','decay','smooth'))
    model=torch.nn.Sequential(torch.nn.Linear(1261,cfg['width']),torch.nn.ReLU(),torch.nn.Linear(cfg['width'],8100))
    model.load_state_dict(payload['state_dict']); model.eval()
    with torch.inference_mode():
        logits=model(x).masked_fill(~mask,float('-inf'))
        predictions=logits.argmax(-1)
        losses=torch.nn.functional.cross_entropy(logits,y,reduction='none')
        assert torch.isfinite(losses).all()
        correct=predictions==y
    rows.append(dict(config=cfg['id'],seed=seed,checkpoint_sha256=sha256(path.read_bytes()).hexdigest(),correct=int(correct.sum()),positions=len(labels),agreement=float(correct.float().mean()),cross_entropy=float(losses.mean()),by_source={source:dict(positions=sum(l.source_id==source for l in labels),correct=sum(bool(correct[i]) for i,l in enumerate(labels) if l.source_id==source)) for source in sorted({l.source_id for l in labels})}))
summary=[]
for cfg in selection['candidates']:
 group=[r for r in rows if r['config']==cfg['id']]
 summary.append(dict(config=cfg['id'],agreement=mean(r['agreement'] for r in group),agreement_std=pstdev(r['agreement'] for r in group),cross_entropy=mean(r['cross_entropy'] for r in group),correct_counts=[r['correct'] for r in group]))
report=dict(selection_sha256=sha256((root/'selection.json').read_bytes()).hexdigest(),dataset_sha256=fresh.digest,role='All new source games are final-test-only regardless of the generator split tags.',generated_labels=len(fresh.labels),excluded_overlaps=len(fresh.labels)-len(labels),retained_test_inputs=[l.input_sha256 for l in labels],source_counts=dict(Counter(l.source_id for l in labels)),random_legal_agreement=float((1/mask.sum(-1).float()).mean()),random_legal_cross_entropy=float(mask.sum(-1).float().log().mean()),trials=rows,summary=summary)
(root/'final-test-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'generated':len(fresh.labels),'retained':len(labels),'summary':summary},indent=2))

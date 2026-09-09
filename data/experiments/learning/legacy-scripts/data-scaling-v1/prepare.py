import json
from pathlib import Path
from qi.learning.data import Dataset, teacher_identity
from qi.learning.experiment import LearningPlan, preview

root=Path(__file__).resolve().parent
raw=Dataset.model_validate_json((root/'dataset.json').read_text())
previous=[Path('artifacts/learning/smoke-v1.json'),Path('artifacts/learning/generalization-v1/dataset.json'),Path('artifacts/learning/tuning-v1/fresh-test-data.json')]
seen=set()
for path in previous:
    data=json.loads(path.read_text())
    seen.update(label['input_sha256'] for label in data['labels'])
# Remove all previously inspected inputs in both splits, before any fitting.
kept=[label for label in raw.labels if label.input_sha256 not in seen]
filtered=Dataset.model_validate(raw.model_copy(update={'labels':kept}).model_dump())
assert not seen.intersection(label.input_sha256 for label in filtered.labels)
assert teacher_identity(filtered.labels[0].analysis)==teacher_identity(raw.labels[0].analysis)
p=root/'curve-data.json'
with p.open('x') as f: f.write(filtered.model_dump_json()+'\n')
selection=json.loads((root/'selection.json').read_text())
plan=LearningPlan(**{k:selection[k] for k in ['sizes','seeds','subset_seed','steps','learning_rate','device','fit_seconds','total_seconds']})
manifest=preview(filtered,filtered.reserved_corpus,plan)
result=dict(raw_dataset_sha256=raw.digest,dataset_sha256=filtered.digest,excluded_files=[str(p) for p in previous],excluded_input_count=len(seen),removed=len(raw.labels)-len(kept),train=len(filtered.split_labels('train')),validation=len(filtered.split_labels('validation')),train_games=len([s for s in filtered.sources if s.split=='train']),validation_games=len([s for s in filtered.sources if s.split=='validation']),planned_trials=manifest['planned_trials'])
(root/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)

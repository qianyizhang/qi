import json
from pathlib import Path
from threading import Lock
from time import perf_counter
from qi.evaluation import Corpus
from qi.learning.data import generate
from qi.teacher import TeacherConfig, analyze

root = Path(__file__).resolve().parent
config = dict(seed=211, games=1056, plies=32, samples=16, seconds=7200, workers=4)
plan = dict(generation=config, sizes=[768,3072,12288], seeds=[7,17,27], subset_seed=7, steps=200, learning_rate=.01, device='mps', fit_seconds=600, total_seconds=7200, teacher_nodes=1000, teacher_depth=3, purpose='Fixed model, teacher and sampling distribution; data-size learning curve. No selection or tuning on fresh validation.')
plan['exclude_previously_inspected_inputs_from']=['artifacts/learning/smoke-v1.json','artifacts/learning/generalization-v1/dataset.json','artifacts/learning/tuning-v1/fresh-test-data.json']
(root/'selection.json').write_text(json.dumps(plan,indent=2)+'\n')
engine = TeacherConfig(Path('artifacts/teachers/pikafish-2026-01-02/MacOS/pikafish-apple-silicon'),Path('artifacts/teachers/pikafish-2026-01-02/pikafish.nnue'),nodes=1000,depth=3)
lock=Lock()
count=0
started=perf_counter()
def labeler(game, teacher):
    global count
    result=analyze(game,teacher)
    with lock:
        count+=1
        if count%256==0:
            print(json.dumps(dict(labels=count,seconds=round(perf_counter()-started,2))),flush=True)
    return result
output=root/'dataset.json'
if output.exists(): raise RuntimeError('Refusing overwrite')
data=generate(Corpus.model_validate_json(Path('data/evaluation/search-positions-v1.json').read_text()),engine,**config,labeler=labeler)
with output.open('x') as stream: stream.write(data.model_dump_json()+'\n')
result=dict(status='complete',train=len(data.split_labels('train')),validation=len(data.split_labels('validation')),sources=len(data.sources),sha256=data.digest,seconds=perf_counter()-started)
(root/'generation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)

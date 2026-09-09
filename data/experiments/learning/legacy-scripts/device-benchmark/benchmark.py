"""Local CPU/MPS timing probe; repeated examples measure throughput, not learning."""
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import time

import torch
from qi.learning.data import Dataset
from qi.learning.train import tensors
from qi.players.policy.runtime import make_model

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).with_name('results.json')
STEPS = 200
REPEATS = 3
CONFIGS = [('cpu', 1), ('cpu', 4), ('cpu', 6), ('mps', 1)]
assert torch.backends.mps.is_available(), 'Actual GPU access is required'
assert os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK') != '1', 'CPU fallback must be disabled'
torch.set_num_threads(1)
start = time.perf_counter()
data_path = ROOT / 'artifacts/learning/smoke-v1.json'
data = Dataset.model_validate_json(data_path.read_text())
base = tensors(data.split_labels('train'))
prep_seconds = time.perf_counter() - start

def synchronize(device):
    if device == 'mps':
        torch.mps.synchronize()

def run(device, threads, batch_size, steps=STEPS):
    torch.set_num_threads(threads)
    torch.manual_seed(7)
    synchronize(device)
    started = time.perf_counter()
    model = make_model().to(device)
    multiplier = batch_size // len(base[0])
    features, mask, targets = [tensor.repeat((multiplier,) + (1,) * (tensor.ndim - 1)).to(device) for tensor in base]
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    loss_fn = torch.nn.CrossEntropyLoss()
    synchronize(device)
    loop_start = time.perf_counter()
    initial_loss = None
    for _ in range(steps):
        optimizer.zero_grad()
        loss = loss_fn(model(features).masked_fill(~mask, float('-inf')), targets)
        # Match production's per-step finite check, including its GPU synchronization.
        if not torch.isfinite(loss):
            raise RuntimeError('Nonfinite training loss')
        if initial_loss is None:
            initial_loss = float(loss.detach())
        loss.backward()
        optimizer.step()
    synchronize(device)
    loop_end = time.perf_counter()
    model.eval()
    with torch.inference_mode():
        logits = model(features).masked_fill(~mask, float('-inf'))
        final_loss = float(loss_fn(logits, targets))
        predictions = logits.argmax(dim=1).cpu()
        agreement = float((predictions == targets.cpu()).float().mean())
        # Check deployment portability by transferring final weights to the CPU.
        cpu_model = model.to('cpu')
        cpu_predictions = cpu_model(features.cpu()).masked_fill(~mask.cpu(), float('-inf')).argmax(dim=1)
        reload_device_agreement = float((cpu_predictions == predictions).float().mean())
    synchronize(device)
    ended = time.perf_counter()
    return dict(device=device, threads=threads, batch_size=batch_size, steps=steps,
                setup_seconds=loop_start-started, optimization_seconds=loop_end-loop_start,
                train_and_cpu_check_seconds=ended-started, initial_loss=initial_loss,
                final_loss=final_loss, training_agreement=agreement,
                gpu_vs_cpu_final_predictions_agreement=reload_device_agreement)

result = dict(torch_version=torch.__version__, platform=platform.platform(), cpu_count=os.cpu_count(),
              mps_available=torch.backends.mps.is_available(),
              fallback_environment=os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK'),
              dataset_sha256=hashlib.sha256(data_path.read_bytes()).hexdigest(),
              script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              preparation_seconds=prep_seconds, steps=STEPS, repeats=REPEATS,
              note='96 actual training inputs; 768 repeats those inputs eight times for throughput only. '
                   'Same initial weights, full-batch masked CE, Adam, float32, lr .01, finite check every step. '
                   'Warm repeated trials; excludes labeling, replay/tensor preparation, validation and disk IO. '
                   'CPU check measures weight transfer and prediction consistency, not serialization.',
              warmups=[], trials=[], summary=[])
for batch in (96, 768):
    for device, threads in CONFIGS:
        warmup=run(device, threads, batch, steps=10)
        result['warmups'].append(warmup)
        print('warmup', batch, device, threads, round(warmup['train_and_cpu_check_seconds'],3), flush=True)
    for repeat in range(REPEATS):
        configs=CONFIGS.copy()
        random.Random(101+repeat).shuffle(configs)
        for device, threads in configs:
            trial=run(device, threads, batch)
            trial['repeat']=repeat
            result['trials'].append(trial)
            OUTPUT.write_text(json.dumps(result, indent=2)+'\n')
            print(json.dumps(trial), flush=True)
for batch in (96, 768):
    for device, threads in CONFIGS:
        trials=[t for t in result['trials'] if (t['batch_size'],t['device'],t['threads']) == (batch,device,threads)]
        timings=[t['optimization_seconds'] for t in trials]
        result['summary'].append(dict(batch_size=batch,device=device,threads=threads,
            median_seconds=statistics.median(timings),min_seconds=min(timings),max_seconds=max(timings),
            median_train_and_cpu_check_seconds=statistics.median(t['train_and_cpu_check_seconds'] for t in trials)))
OUTPUT.write_text(json.dumps(result,indent=2)+'\n')
print('SUMMARY', json.dumps(result['summary']), flush=True)

"""Reproducible training, independent tests, workload shift and calibration."""
import argparse
import csv
import json
import platform
from pathlib import Path
import numpy as np
import sklearn
from sklearn.tree import DecisionTreeClassifier
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from schedulers import POLICIES, schedule

FEATURES = ['mean_track', 'variance', 'mean_adjacent_jump', 'fraction_below_head',
            'unique_fraction', 'mean_distance_from_head', 'head_position']

def workload(rng, kind, n=24):
    if kind == 'random':
        return rng.integers(0, 200, n).tolist()
    if kind == 'sequential':
        start = int(rng.integers(0, 200))
        step = int(rng.choice([-3, -2, -1, 1, 2, 3]))
        return [int(np.clip(start+i*step, 0, 199)) for i in range(n)]
    center = int(rng.integers(10, 190))
    return [int(rng.integers(0, 200)) if rng.random() < .15 else
            int(np.clip(round(rng.normal(center, 6)), 0, 199)) for _ in range(n)]

def features(q, h):
    a = np.array(q)
    return [float(a.mean()), float(a.var()), float(np.abs(np.diff(a)).mean()),
            float((a <= h).mean()), len(set(q))/len(q),
            float(np.abs(a-h).mean()), h]

def costs(q, h):
    return [schedule(q, h, p)[0] for p in POLICIES]

def write_csv(path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=307)
    parser.add_argument('--output', default='results')
    args = parser.parse_args()
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    train_rng = np.random.default_rng(args.seed)
    test_rng = np.random.default_rng(args.seed+1)
    kinds = ['sequential', 'random', 'bursty']
    X, y, training = [], [], []
    for i in range(1200):
        kind = kinds[i % 3]; q = workload(train_rng, kind)
        h = int(train_rng.integers(0, 200)); c = costs(q, h)
        # Deterministic canonical label; test correctness accepts all minimum ties.
        label = int(np.argmin(c))
        X.append(features(q, h)); y.append(label)
        training.append(dict(sample=i, kind=kind, head=h, requests=json.dumps(q),
                             label=POLICIES[label], **dict(zip(POLICIES, c))))
    model = DecisionTreeClassifier(max_depth=5, min_samples_leaf=20,
                                   random_state=args.seed).fit(X, y)
    rows = []
    def evaluate(q, h, kind, phase, index, experiment):
        c = costs(q, h); proba = model.predict_proba([features(q, h)])[0]
        pred = int(model.classes_[int(np.argmax(proba))])
        rows.append(dict(experiment=experiment, window=index, phase=phase,
                         kind=kind, head=h, requests=json.dumps(q),
                         selected=POLICIES[pred], confidence=float(max(proba)),
                         correct=int(c[pred] == min(c)), regret=c[pred]-min(c),
                         selected_movement=c[pred], oracle_movement=min(c),
                         **dict(zip(POLICIES, c))))
        return schedule(q, h, POLICIES[pred])[1][-1]
    for kind in kinds:
        for i in range(150):
            evaluate(workload(test_rng, kind), int(test_rng.integers(0, 200)),
                     kind, 'standalone', i, 'independent')
    # Shared-window comparison: all policies see the same queue and initial head.
    # Timeline head is carried from the selected scheduler's preceding window.
    h = 53
    for i in range(100):
        kind = 'sequential' if i < 50 else 'bursty'
        h = evaluate(workload(test_rng, kind), h, kind,
                     'before' if i < 50 else 'after', i, 'shift')
    write_csv(out/'training.csv', training)
    write_csv(out/'raw_results.csv', rows)
    groups = {k:[r for r in rows if r['experiment']=='independent' and r['kind']==k] for k in kinds}
    groups.update({p:[r for r in rows if r['phase']==p] for p in ['before','after']})
    summary = []
    for name, data in groups.items():
        summary.append(dict(group=name, windows=len(data), accuracy=np.mean([r['correct'] for r in data]),
            mean_regret=np.mean([r['regret'] for r in data]),
            **{p:sum(r[p] for r in data) for p in POLICIES},
            selected=sum(r['selected_movement'] for r in data),
            oracle=sum(r['oracle_movement'] for r in data)))
    write_csv(out/'summary.csv', summary)
    bins = []
    for lo in [0,.2,.4,.6,.8]:
        data = [r for r in rows if lo <= r['confidence'] and (r['confidence'] < lo+.2 or lo==.8)]
        if data:
            bins.append(dict(lower=lo, count=len(data), mean_confidence=np.mean([r['confidence'] for r in data]),
                             accuracy=np.mean([r['correct'] for r in data])))
    write_csv(out/'calibration.csv', bins)
    confidence_by_correct = {str(v):float(np.mean([r['confidence'] for r in rows if r['correct']==v]))
                             if any(r['correct']==v for r in rows) else None for v in [0,1]}
    metadata = dict(seed=args.seed, python=platform.python_version(), platform=platform.platform(),
                    numpy=np.__version__, sklearn=sklearn.__version__, features=FEATURES,
                    training_labels={p:y.count(i) for i,p in enumerate(POLICIES)},
                    confidence_by_correct=confidence_by_correct,
                    feature_importance=dict(zip(FEATURES, model.feature_importances_.tolist())))
    (out/'metadata.json').write_text(json.dumps(metadata, indent=2))
    fig, ax = plt.subplots(figsize=(9,4))
    xx=np.arange(len(summary)); width=.14
    for j,p in enumerate([*POLICIES,'selected']):
        ax.bar(xx+(j-2)*width,[s[p]/s['windows'] for s in summary],width,label=p)
    ax.set_xticks(xx, [s['group'] for s in summary]); ax.set_ylabel('Mean head movement (tracks/window)')
    ax.legend(ncol=5, fontsize=8); fig.tight_layout(); fig.savefig(out/'comparison.png',dpi=180); plt.close(fig)
    fig,ax=plt.subplots(figsize=(5,4)); ax.plot([0,1],[0,1],'--',color='gray')
    ax.plot([b['mean_confidence'] for b in bins],[b['accuracy'] for b in bins],'o-')
    ax.set(xlabel='Mean predicted confidence',ylabel='Observed tie-aware accuracy',xlim=(0,1),ylim=(0,1))
    fig.tight_layout(); fig.savefig(out/'calibration.png',dpi=180); plt.close(fig)
    timeline=[r for r in rows if r['experiment']=='shift']
    fig,ax=plt.subplots(figsize=(9,4))
    for p in [*POLICIES,'selected_movement']:
        ax.plot([r['window'] for r in timeline],np.cumsum([r[p] for r in timeline]),label=p)
    ax.axvline(49.5,color='black',linestyle='--'); ax.set(xlabel='Window (shift at 50)',ylabel='Cumulative head movement (tracks)')
    ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(out/'shift.png',dpi=180); plt.close(fig)
    print(json.dumps(summary,indent=2)); print('Confidence by correctness:',confidence_by_correct)
if __name__ == '__main__':
    main()

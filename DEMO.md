# 3–5 minute walkthrough

1. Explain that requests are cylinder numbers in a synthetic HDD simulation.
2. Open schedulers.py: arrival order, nearest request, downward sweep, circular wrap.
3. Run `python -m unittest discover -s tests -v` and show the lecture totals.
4. Open experiment.py: show workload generation, seven features and decision tree.
5. Explain separate random seeds and no testing information used for training.
6. Run `python experiment.py` and open results/comparison.png and shift.png.
7. Explain the shift at window 50 and why SSTF can outperform the selector.
8. Show calibration.png: compare predicted confidence with actual correctness.
9. State limits: shared starting heads; direction reset; synthetic queues; tracks rather than ms.

Try these questions before presenting:
- Why is the 0-to-199 return charged in C-SCAN?
- What distinguishes SCAN from LOOK?
- Why does a decision tree sometimes select a worse scheduler?
- What does a confidence of 0.8 mean, and how can you check it?
- Why is hardware timing inside VirtualBox different from this experiment?

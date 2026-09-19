# Thesis work

Not delegated to a small model, and not a retrieval task: it is a judgement call
about what can be finished, defended, and supervised.

## The constraint

The thesis project is **presented to the students' cohort on 16 October 2026**,
with Marco Corazza. In-person teaching starts 12 October. A topic without a
supervisor who is physically in the room that week is a worse topic than a
duller one that has one.

## What decides the topic

1. **A supervisor present in Module 8.** Corazza (portfolio optimisation,
   metaheuristics), Fasano (metaheuristics for finance), Raggi (financial time
   series), Costola (LLMs for finance), De Nobili (tensor networks),
   Ferrara (quantum finance).
2. **Feasibility on one 8 GB GPU.** Anything needing real quantum hardware time
   or a large training run is not a master's thesis on this timeline.
3. **Work already done.** `Personale/QML/pyhtonTest` is a QUBO knapsack
   benchmark (Pyomo/Gurobi, Qiskit eigensolver, D-Wave `neal`, up to n=100).

## Procedure

- Search the index for the candidate supervisors' own topics before proposing
  anything: `kb_search "portfolio optimisation" module="M8"`.
- For each candidate direction produce: research question, dataset, classical
  baseline, evaluation metric, and an honest compute estimate.
- Write to `vault/20-thesis/`. Shortlist first, proposal second.

## Rules

- No topic without a named baseline to beat. "Explore X with QML" is not a
  thesis.
- State the compute cost in hours on the actual hardware, not in principle.
- If a direction depends on material not yet in the corpus, say so explicitly
  rather than reasoning around the gap.

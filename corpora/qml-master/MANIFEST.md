# Manifest — qml-master

Hand-written overrides for files the rules in `corpus.yaml` cannot place, and
the switch for sources that should stay out of the index.

**Deciding what belongs in the corpus is a decision made here, never in code.**
Run `studykb ingest --corpus qml-master --dry-run`; anything it lists as
unassigned belongs in the table below.

Columns: `path | module | type | enabled`. Leave `type` empty to keep what
discovery guessed; `enabled: false` excludes the file.

| path | module | type | enabled |
|---|---|---|---|
| Book/Michael A. Nielsen, Isaac L. Chuang - Quantum Computation and Quantum Information_ 10th Anniversary Edition (2011, Cambridge University Press).pdf | M4 | book | |
| Book/Machine Learning with Quantum Computers (Quantum Science and -- Maria Schuld;Francesco Petruccione.pdf | M7 | book | |
| Book/Quantum Machine Learning _ Thinking and Exploration in -- Claudio Conti.pdf | M7 | book | |
| Book/Tacchino_PhDThesis.pdf | M7 | book | |
| Book/[Scienza e idee 258] Leonard Susskind, Art Friedman - Meccanica quantistica. Il minimo indispensabile per fare della (buona) fisica (2015, Cortina Raffaello) - libgen.li.pdf | M3 | book | |
| Book/[Theoria] Gian Carlo Ghirardi - Un'occhiata alle carte di Dio. Gli interrogativi che la scienza moderna pone all'uomo (1997, Il Saggiatore) - libgen.li.pdf | M3 | book | |
| Book/3G Editorial Board - Quantum Blockchain (2023) - libgen.li.pdf | M9 | book | |
| Book/Landau. Lifshitz - Meccanica quantistica Teoria non relativistica (Fisica Teorica 3) - Mir - 1994.pdf | M3 | book | false |
| Book/Landau_Lifshitz_T2_short.pdf | M3 | book | false |
| slides1.pdf | M4 | slides | |
| deep-learning.pptx | M2 | slides | |
| FCaruso_From Quantum Computing to Quantum AI_2026.pdf | M4 | slides | |
| ML Notes_v1.pdf | M2 | paper | |
| Parigi2024_Quantum‐Noise‐Driven-Generative-Diffusion-Models.pdf | M5 | paper | |
| Zhang2026-Generative-Quantum-Machine-Learning-via-Denoising-Diffusion-Probabilistic-Models.pdf | M5 | paper | |
| [Quantum Machine Intelligence 2026-jun vol. 8 iss. 1] Benchmarking quantum machine learning methods for intrusion detection on noisy quantum computers{Cirillo, Franco (author)_Esposito, Christian (author)_Taek Seo, Jung (author)}(2026 Ju...{115750754}.pdf | M9 | paper | |
| pyhtonTest/QKnapsack.pdf | M7 | paper | |

## Notes on the disabled entries

Landau & Lifshitz is out of scale for a 24-hour introductory module: 1,144 pages
of graduate theory against a course that needs the formalism, not the full
treatment. Flip `enabled` to `true` if that changes — it is one word, and the
next ingest picks the book up.

## Module ids

From the course timetable, parsed by `studykb`. `kb_outline M8` prints any of
them lecture by lecture.

| id | module | when |
|---|---|---|
| M1 | Preliminaries (maths, statistics, Python, data protection) | Mar–Jul 2026 |
| M2 | Classical Machine Learning | Mar–Jun 2026 |
| M3 | Introduction to Quantum Mechanics | Apr–May 2026 |
| M4 | From Quantum Computing to Quantum AI | May–Jun 2026 |
| M5 | Towards QML applications | Jun 2026 |
| M6 | Real Quantum Processors | Jun 2026 |
| M7 | Quantum Machines Deep Learning | Sep 2026 |
| M8 | Quantum Machine Learning for Finance | Oct–Nov 2026, in person |
| M9 | Quantum Applications | Oct–Nov 2026, in person |

Nothing is assigned to M1, M6 or M8 yet: the material for those modules is not
in the corpus. M6 (IBM Qiskit, noise mitigation) and M8 are the gaps worth
chasing.

# Manifest — qml-master

Hand-written overrides for files the rules in `corpus.yaml` cannot place, and
the switch for sources that should stay out of the index.

**Deciding what belongs in the corpus is a decision made here, never in code.**
Run `studykb ingest --corpus qml-master --dry-run`; anything it lists as
unassigned belongs in the table below.

Columns: `path | module | type | enabled`. Leave `type` empty to keep what
discovery guessed from the folder; `enabled: false` excludes the file.

The corpus root holds study material and nothing else, so the folder already
says the type: `books/` → book, `papers/` → paper, `slides/` → slides,
`transcripts/` → transcript. Folders are flat on purpose. A file's path is its
identity: moving it between folders makes a second source under the new path
while the old chunks stay behind, so classification is changed **here**, by
editing a line, and a corrected module now re-indexes that one source.

| path | module | type | enabled |
|---|---|---|---|
| books/3G Editorial Board - Quantum Blockchain (2023) - libgen.li.pdf | M9 |  |  |
| books/Landau. Lifshitz - Meccanica quantistica Teoria non relativistica (Fisica Teorica 3) - Mir - 1994.pdf | M3 |  | false |
| books/Landau_Lifshitz_T2_short.pdf | M3 |  | false |
| books/Machine Learning with Quantum Computers (Quantum Science and -- Maria Schuld;Francesco Petruccione.pdf | M7 |  |  |
| books/Michael A. Nielsen, Isaac L. Chuang - Quantum Computation and Quantum Information_ 10th Anniversary Edition (2011, Cambridge University Press).pdf | M4 |  |  |
| books/Quantum Machine Learning _ Thinking and Exploration in -- Claudio Conti.pdf | M7 |  |  |
| books/Tacchino_PhDThesis.pdf | M7 |  |  |
| books/[Scienza e idee 258] Leonard Susskind, Art Friedman - Meccanica quantistica. Il minimo indispensabile per fare della (buona) fisica (2015, Cortina Raffaello) - libgen.li.pdf | M3 |  |  |
| books/[Theoria] Gian Carlo Ghirardi - Un'occhiata alle carte di Dio. Gli interrogativi che la scienza moderna pone all'uomo (1997, Il Saggiatore) - libgen.li.pdf | M3 |  |  |
| papers/3743128.pdf | M2 |  |  |
| papers/EvansRosenthal2009.pdf | M1 |  |  |
| papers/ML Notes_v1.pdf | M2 |  |  |
| papers/Parigi2024_Quantum‐Noise‐Driven-Generative-Diffusion-Models.pdf | M5 |  |  |
| papers/Quantum convolutional neural networks.pdf | M7 |  |  |
| papers/Zhang2026-Generative-Quantum-Machine-Learning-via-Denoising-Diffusion-Probabilistic-Models.pdf | M5 |  |  |
| papers/[Quantum Machine Intelligence 2026-jun vol. 8 iss. 1] Benchmarking quantum machine learning methods for intrusion detection on noisy quantum computers{Cirillo, Franco (author)_Esposito, Christian (author)_Taek Seo, Jung (author)}(2026 Ju...{115750754}.pdf | M9 |  |  |
| papers/mathematics-11-03947-v2.pdf | M9 |  |  |
| slides/FCaruso_From Quantum Computing to Quantum AI_2026.pdf | M4 |  |  |
| slides/Master_QUANTUM_MACHINE_LEARNING-CORAZZA-Preliminaries-Slides.pdf | M1 |  |  |
| slides/deep-learning.pptx | M2 |  |  |
| slides/lect5_testing.pdf | M1 |  |  |
## Notes on the disabled entries

Landau & Lifshitz is out of scale for a 24-hour introductory module: 1,144 pages
of graduate theory against a course that needs the formalism, not the full
treatment. Flip `enabled` to `true` if that changes — it is one word, and the
next ingest picks the book up.

## Not indexed yet

The seven `.ipynb` tutorials under `papers/` (PennyLane, Deutsch-Jozsa, Grover,
Grover-Sudoku, QGAN ×2, Qiskit). `.ipynb` is not in `extract.SUPPORTED`, so they
are skipped in silence. Their markdown cells are prose worth indexing and an
extractor is ~20 lines of stdlib, but it does not exist yet.

## Classifications checked against the timetable

Seven files had a module in this table that disagreed with the folder they had
been put in, and four more were unplaced. Each was settled by reading what the
calendar says the module actually covered, not by the filename:

| file | was | is | why |
|---|---|---|---|
| Nielsen & Chuang | M3 folder | **M4** | M3 is Droghetti's quantum physics; this is gates and circuits |
| Schuld, Conti, Tacchino | M4 folder | **M7** | M7 is "QML algorithms and examples" |
| Quantum Blockchain | M7 folder | **M9** | M9 covers quantum cryptography and industrial application |
| Zhang2026 (denoising diffusion) | M6 folder | **M5** | M5 is literally "Tutorial on Quantum Generative AI" |
| Benchmarking / intrusion detection | M5 folder | **M9** | an application paper; the noise angle made M6 arguable |
| `3743128.pdf` | M1 folder | **M2** | it is a survey of Kolmogorov-Arnold Networks — classical deep learning |
| `mathematics-11-03947-v2.pdf` | M4 folder | **M9** | "A Quantum-Resistant Blockchain System" |
| `Quantum convolutional neural networks.pdf` | M5 folder | **M7** | Cong/Choi/Lukin QCNN: a QML algorithm, not generative |
| `lect5_testing.pdf` | unplaced paper | **M1, slides** | Raggi's Beamer deck "Preliminary statistics — Hypothesis Testing" |

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

M6 and M8 have no material at all, and they are the gaps worth chasing: M6 is
IBM Qiskit and noise mitigation, M8 is the 8-CFU finance module.

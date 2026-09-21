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
`code/` → code, `transcripts/` → transcript. Folders are flat on purpose. A
file's path is its identity: moving it between folders makes a second source
under the new path while the old chunks stay behind, so classification is
changed **here**, by editing a line, and a corrected module re-indexes that one
source.

| path                                                                                                                                                                                                                                                                   | module | type | enabled |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ---- | ------- |
| books/3G Editorial Board - Quantum Blockchain (2023) - libgen.li.pdf                                                                                                                                                                                                   | M9     |      |         |
| books/Handouts__FASANO_QML_2025-2026_iperref.pdf                                                                                                                                                                                                                       | M1     |      |         |
| books/Landau. Lifshitz - Meccanica quantistica Teoria non relativistica (Fisica Teorica 3) - Mir - 1994.pdf                                                                                                                                                            | M3     |      | false   |
| books/Landau_Lifshitz_T2_short.pdf                                                                                                                                                                                                                                     | M3     |      | false   |
| books/Machine Learning with Quantum Computers (Quantum Science and -- Maria Schuld;Francesco Petruccione.pdf                                                                                                                                                           | M7     |      |         |
| books/Michael A. Nielsen, Isaac L. Chuang - Quantum Computation and Quantum Information_ 10th Anniversary Edition (2011, Cambridge University Press).pdf                                                                                                               | M4     |      |         |
| books/Quantum Machine Learning A Hands-on Tutorial for Machine Learning Practitioners and Researchers.pdf                                                                                                                                                              | M7     |      |         |
| books/Quantum Machine Learning _ Thinking and Exploration in -- Claudio Conti.pdf                                                                                                                                                                                      | M7     |      |         |
| books/Tacchino_PhDThesis.pdf                                                                                                                                                                                                                                           | M7     |      |         |
| books/QuickIntroToPython.pdf                                                                                                                                                                                                                                           | M1     |      |         |
| code/01_PCA_2.ipynb                                                                                                                                                                                                                                                    | M2     |      |         |
| code/02_KMeans.ipynb                                                                                                                                                                                                                                                   | M2     |      |         |
| code/03_HierarchicalClustering.ipynb                                                                                                                                                                                                                                   | M2     |      |         |
| code/04_tSNE_UMAP.ipynb                                                                                                                                                                                                                                                | M2     |      |         |
| code/05_CNN.ipynb                                                                                                                                                                                                                                                      | M2     |      |         |
| code/05_CNN_segmentation.ipynb                                                                                                                                                                                                                                         | M2     |      |         |
| code/1_Basic_intro_qiskit_and_noise_Sampler.ipynb                                                                                                                                                                                                                      | M6     |      |         |
| code/2_classification.ipynb                                                                                                                                                                                                                                            | M2     |      |         |
| code/2_example_Shor.ipynb                                                                                                                                                                                                                                              | M6     |      |         |
| code/3_focal.ipynb                                                                                                                                                                                                                                                     | M2     |      |         |
| code/3_simplified_Shor.ipynb                                                                                                                                                                                                                                           | M6     |      |         |
| code/4.5_classification_exercise.ipynb                                                                                                                                                                                                                                 | M2     |      |         |
| code/4_Shor.ipynb                                                                                                                                                                                                                                                      | M6     |      |         |
| code/4_pretraining.ipynb                                                                                                                                                                                                                                               | M2     |      |         |
| code/5_advanced_Shor.ipynb                                                                                                                                                                                                                                             | M6     |      |         |
| code/5_detection.ipynb                                                                                                                                                                                                                                                 | M2     |      |         |
| code/6_open-world-detection.ipynb                                                                                                                                                                                                                                      | M2     |      |         |
| code/7_od_exercise (1).ipynb                                                                                                                                                                                                                                           | M2     |      |         |
| code/GroverTutorial.ipynb                                                                                                                                                                                                                                              | M6     |      |         |
| code/NB1_MNIST_stud.ipynb                                                                                                                                                                                                                                              | M2     |      |         |
| code/NB2_FashionMNIST.ipynb                                                                                                                                                                                                                                            | M2     |      |         |
| code/QK.ipynb                                                                                                                                                                                                                                                          | M6     |      |         |
| code/QML - Classification SVM.ipynb                                                                                                                                                                                                                                    | M2     |      |         |
| code/QML - Decision Tree.ipynb                                                                                                                                                                                                                                         | M2     |      |         |
| code/QML - Neural Network MLP PyTorch.ipynb                                                                                                                                                                                                                            | M2     |      |         |
| code/QML Knn - NaiveBayes.ipynb                                                                                                                                                                                                                                        | M2     |      |         |
| code/QML- Clustering - DBScan.ipynb                                                                                                                                                                                                                                    | M2     |      |         |
| code/QML- Clustering K-Means and Hierarchical Clustering.ipynb                                                                                                                                                                                                         | M2     |      |         |
| code/README.md                                                                                                                                                                                                                                                         | M6     |      | false   |
| code/Solution_0-Setup.ipynb                                                                                                                                                                                                                                            | M6     |      |         |
| code/Solution_1-QuantumRouteOptimisation.ipynb                                                                                                                                                                                                                         | M6     |      |         |
| code/Untitled0.ipynb                                                                                                                                                                                                                                                   | M2     |      |         |
| code/cnn_pytorch.ipynb                                                                                                                                                                                                                                                 | M2     |      |         |
| code/decision_tree.ipynb                                                                                                                                                                                                                                               | M2     |      |         |
| code/mlp_sklearn_pytorch.ipynb                                                                                                                                                                                                                                         | M2     |      |         |
| code/qiskitTutorial final version.ipynb                                                                                                                                                                                                                                | M4     |      |         |
| code/report.md                                                                                                                                                                                                                                                         | M6     |      |         |
| code/tutorialDJ.ipynb                                                                                                                                                                                                                                                  | M4     |      |         |
| code/tutorialGrover.ipynb                                                                                                                                                                                                                                              | M4     |      |         |
| code/tutorialGroverSudoku.ipynb                                                                                                                                                                                                                                        | M4     |      |         |
| code/tutorialPennylane.ipynb                                                                                                                                                                                                                                           | M5     |      |         |
| code/tutorialQGANHybrid.ipynb                                                                                                                                                                                                                                          | M5     |      |         |
| code/tutorialQGANQuantum.ipynb                                                                                                                                                                                                                                         | M5     |      |         |
| papers/Assessment - July 3rd - Modules 4, 5 and 6_ Attempt review _ Ca' Foscari.pdf                                                                                                                                                                                    |        |      |         |
| papers/Assessment - May 22nd - Modules 1, 2, 3_ Attempt review _ Ca' Foscari.pdf                                                                                                                                                                                       |        |      |         |
| papers/EvansRosenthal2009.pdf                                                                                                                                                                                                                                          | M1     |      |         |
| papers/Kernel-based training of quantum models with scikit-learn _ PennyLane Demos.pdf                                                                                                                                                                                 | M5     |      |         |
| papers/Lecture4 (spins_and_qubits).pdf                                                                                                                                                                                                                                 | M3     |      |         |
| papers/ML Notes_v1.pdf                                                                                                                                                                                                                                                 | M2     |      |         |
| papers/Parigi2024_Quantum‐Noise‐Driven-Generative-Diffusion-Models.pdf                                                                                                                                                                                                 | M5     |      |         |
| papers/Quantum Machine Learning and Deep Learning: Fundamentals, Algorithms, Techniques, and Real-World Applications .pdf                                                                                                                                              | M7     |      |         |
| papers/Quantum artificial intelligence: A survey.pdf                                                                                                                                                                                                                   | M7     |      |         |
| papers/Quantum convolutional neural networks.pdf                                                                                                                                                                                                                       | M7     |      |         |
| papers/Quanvolutional Neural Networks _ PennyLane Demos.pdf                                                                                                                                                                                                            | M5     |      |         |
| papers/Zhang2026-Generative-Quantum-Machine-Learning-via-Denoising-Diffusion-Probabilistic-Models.pdf                                                                                                                                                                  | M5     |      |         |
| papers/[Quantum Machine Intelligence 2026-jun vol. 8 iss. 1] Benchmarking quantum machine learning methods for intrusion detection on noisy quantum computers{Cirillo, Franco (author)_Esposito, Christian (author)_Taek Seo, Jung (author)}(2026 Ju...{115750754}.pdf | M9     |      |         |
| papers/complex_numbers.pdf                                                                                                                                                                                                                                             | M3     |      |         |
| papers/exercise2.1.pdf                                                                                                                                                                                                                                                 | M3     |      |         |
| papers/exercise2.2.pdf                                                                                                                                                                                                                                                 | M3     |      |         |
| papers/exercise3.1.pdf                                                                                                                                                                                                                                                 | M3     |      |         |
| papers/exercise3.2.pdf                                                                                                                                                                                                                                                 | M3     |      |         |
| papers/exercise3.3.pdf                                                                                                                                                                                                                                                 | M3     |      |         |
| papers/exercise4.1.pdf                                                                                                                                                                                                                                                 | M3     |      |         |
| papers/exercise4.2.pdf                                                                                                                                                                                                                                                 | M3     |      |         |
| papers/exercises.pdf                                                                                                                                                                                                                                                   | M3     |      |         |
| papers/exercises_with_solutions.pdf                                                                                                                                                                                                                                    | M3     |      |         |
| papers/lecture_QM_formalism.pdf                                                                                                                                                                                                                                        | M3     |      |         |
| papers/lecture_angular_momentum.pdf                                                                                                                                                                                                                                    | M3     |      |         |
| papers/lectures_formalism1.pdf                                                                                                                                                                                                                                         | M3     |      |         |
| papers/lectures_master_spin_qubit.pdf                                                                                                                                                                                                                                  | M3     |      |         |
| papers/mathematics-11-03947-v2.pdf                                                                                                                                                                                                                                     | M9     |      |         |
| papers/potential_well.pdf                                                                                                                                                                                                                                              | M3     |      |         |
| papers/proof_operators.pdf                                                                                                                                                                                                                                             | M3     |      |         |
| papers/A Survey on Kolmogorov-Arnold Network.pdf | M7 | |  |
| papers/A Survey on Diffusion Models for Time Series and Spatio-Temporal Data.pdf | M5 | |  |
| papers/A brief review of quantum machine learning techniques for financial services.pdf | M8 | |  |
| papers/Assessment - July 3rd - Modules 4, 5 and 6_ Attempt review _ Ca' Foscari.pdf |  | | false |
| papers/Assessment - May 22nd - Modules 1, 2, 3_ Attempt review _ Ca' Foscari.pdf |  | | false |
| papers/Diffusion Models in Finance: A Survey.pdf | M8 | |  |
| papers/QuKAN: A Quantum Circuit Born Machine Approach to Quantum Kolmogorov Arnold Networks.pdf | M7 | |  |
| papers/Quantum Machine Learning A Hands-on Tutorial for Machine Learning Practitioners and Researchers.pdf |  | | false |
| papers/Quantum Machine Learning Fraud Detection Project Achieves Key Technical Milestones.pdf | M7 | |  |
| papers/Quantum-Inspired Hybrid Machine Learning Framework for Scalable Computational Next-Generation Technologies.pdf | M7 | |  |
| slides/002_AI_INTRO.pdf                                                                                                                                                                                                                                                | M2     |      |         |
| slides/003_Machine_Learning_supervised_unsupervised.pdf                                                                                                                                                                                                                | M2     |      |         |
| slides/004_Classification copia.pdf                                                                                                                                                                                                                                    | M2     |      |         |
| slides/005_01_Clustering copia.pdf                                                                                                                                                                                                                                     | M2     |      |         |
| slides/20260905_Algorithms_Foundations_CFCS.pptx.pdf                                                                                                                                                                                                                   | M7     |      |         |
| slides/20260911_Circuit_Design_Embeddings_Frameworks_CFCS.pptx.pdf                                                                                                                                                                                                     | M7     |      |         |
| slides/20260912_Classification_Applications_Limits_CFCS.pptx.pdf                                                                                                                                                                                                       | M7     |      |         |
| slides/CaFoscariQML - ClassificationToDetection (1).pdf                                                                                                                                                                                                                | M2     |      |         |
| slides/FCaruso_From Quantum Computing to Quantum AI_2026.pdf                                                                                                                                                                                                           | M4     |      |         |
| slides/Ligorio_DLMLBasics_MQML_CaFoscari.pdf                                                                                                                                                                                                                           | M2     |      |         |
| slides/Master_Ca_Foscari 2026 - Luca Crippa.pdf                                                                                                                                                                                                                        | M6     |      |         |
| slides/Master_Ca_Foscari 2026 - Tommaso Fioravanti.pdf                                                                                                                                                                                                                 | M6     |      |         |
| slides/Master_QUANTUM_MACHINE_LEARNING-CORAZZA-Preliminaries-Slides.pdf                                                                                                                                                                                                | M1     |      |         |
| slides/PCA.pdf                                                                                                                                                                                                                                                         | M2     |      |         |
| slides/QML Master Executive 2026.pdf                                                                                                                                                                                                                                   | M6     |      |         |
| slides/Shor.pdf                                                                                                                                                                                                                                                        | M6     |      |         |
| slides/Slides_Fasano_QML_2025-2026.pdf                                                                                                                                                                                                                                 | M1     |      |         |
| slides/Slides_master_QML1.pdf                                                                                                                                                                                                                                          | M3     |      |         |
| slides/Slides_master_QML2.pdf                                                                                                                                                                                                                                          | M3     |      |         |
| slides/deep-learning (final version).pptx                                                                                                                                                                                                                              | M2     |      |         |
| slides/deep-learning.pptx                                                                                                                                                                                                                                              | M2     |      | false   |
| slides/hierarchical clustering.pdf                                                                                                                                                                                                                                     | M2     |      |         |
| slides/introduction ML.pdf                                                                                                                                                                                                                                             | M2     |      |         |
| slides/lect2_probability.pdf                                                                                                                                                                                                                                           | M1     |      |         |
| slides/lect3_correlation.pdf                                                                                                                                                                                                                                           | M1     |      |         |
| slides/lect4_sampling.pdf                                                                                                                                                                                                                                              | M1     |      |         |
| slides/lect5_testing.pdf                                                                                                                                                                                                                                               | M1     |      |         |
| slides/lezione2.pdf                                                                                                                                                                                                                                                    | M4     |      |         |
| slides/slides of lesson QML 2025.pdf                                                                                                                                                                                                                                   | M6     |      |         |
| slides/slides1.pdf                                                                                                                                                                                                                                                     | M4     |      |         |
| slides/slidesGM.pdf                                                                                                                                                                                                                                                    | M4     |      |         |
| slides/slidesML2.pdf                                                                                                                                                                                                                                                   | M2     |      |         |
| slides/whiteboard1.pdf                                                                                                                                                                                                                                                 | M4     |      |         |
| slides/whiteboard3.pdf                                                                                                                                                                                                                                                 | M4     |      |         |
| slides/whiteboard4.pdf                                                                                                                                                                                                                                                 | M5     |      |         |
| transcripts/01 – Foundations_ From Neural Networks to Quantum Circuits.docx | M7 | | |
| transcripts/01 – Foundations_ Quantum Hardware, Computational Complexity and the Qubit.docx | M4 | | |
| transcripts/01 – IBM Quantum_ Roadmap, Hardware, Qiskit and Cloud Access.docx | M6 | | |
| transcripts/01 – Noise, Quantum Process Tomography and Randomized Benchmarking.docx | M6 | | |
| transcripts/02 – Hybrid Workflows, MaxCut and QUBO, and Neutral Atom Hardware.docx | M7 | | |
| transcripts/02 – Privacy and Data Protection under the GDPR.docx | M1 | | |
| transcripts/02 – Quantum Error Correction, Fault Tolerance and Shadow Estimation.docx | M6 | | |
| transcripts/02 – Shor, Grover and Variational Algorithms.docx | M6 | | |
| transcripts/02 – The Bloch Sphere, Quantum Gates, Observables and Noise.docx | M4 | | |
| transcripts/03 – Ansatz Design and Encoding Strategy.docx | M7 | | |
| transcripts/03 – Exercise Session_ Gates, Tensor Products and Expected Values.docx | M4 | | |
| transcripts/03 – IBM Quantum Offerings, Use Cases and Quantum-Safe Cryptography.docx | M6 | | |
| transcripts/04 – Correlation Observables, Simulators vs Emulators, and QuTiP.docx | M4 | | |
| transcripts/04 – Frameworks_ PennyLane, Qiskit, and Hybrid PyTorch Models.docx | M7 | | |
| transcripts/04 – Industry Applications and Qiskit Notebooks.docx | M6 | | |
| transcripts/05 – Classical Data Encoding, Image Encoding and Quantum ML Models.docx | M4 | | |
| transcripts/05 – Implementing Deutsch, Deutsch–Jozsa and Grover in Qiskit.docx | M4 | | |
| transcripts/05 – The Full Classification Pipeline_ Iris, Quantum Kernels and ML Methodology.docx | M7 | | |
| transcripts/06 – Finance Applications, Published Case Studies and Drug Discovery.docx | M7 | | |
| transcripts/06 – Grover Sudoku, Quantum Noise Channels, and Classical Generative Models.docx | M4 | | |
| transcripts/07 – Neutral Atom Hardware_ Physics, Industry and Engineering.docx | M7 | | |
| transcripts/07 – Quantum Autoencoders, Quantum GANs and Diffusion Models.docx | M4 | | |
| transcripts/08 – Programming Neutral Atoms_ Pulser, PennyLane and Cross-Modality Benchmarks.docx | M7 | | |
| transcripts/08 – Quantum Diffusion Models and Introduction to PennyLane.docx | M5 | | |
| transcripts/09 – Business Cases, NISQ Limits, Barren Plateaus, and Introduction to Annealing.docx | M7 | | |
| transcripts/09 – Hybrid Models in PennyLane and PyTorch, and a Quantum GAN.docx | M5 | | |
| transcripts/10 – Quantum Annealing_ Josephson Junctions, the Adiabatic Theorem and QUBO.docx | M7 | | |
| transcripts/10 – The Machine Learning Pipeline and the Project Laboratory (Morning).docx | M5 | | |
| transcripts/11 – The Project Laboratory_ Quanvolutional Results and Three Group Approaches (Afternoon).docx | M5 | | |

## The transcripts carry no module in their path

Twenty-nine Word write-ups, named `NN – <lesson title>`, so neither module rule
fires: there is no `M<n>` in the path and no date either. The lecturer is not in
the name but on the first line of each file (`Lecturer: …`, `Source transcript:
ZARBO_03`). They are placed here by the same evidence the decks were — **the
timetable says which module each lecturer teaches**. Caruso and Onorati, Crippa, Zarbo and Bernes
each teach one module, so those are settled by the name alone.

Martina teaches two, M4 and M5, so his eleven files are split by what they are
about, against his lecture dates: QC basics and circuit practice (16 and 23 May)
and the generative-AI lectures (5-6 June) are M4; the PennyLane tutorial
(13 June) and the quanvolutional workgroup (20 June) are M5. That is the same
split already applied to `whiteboard3` (M4) and `whiteboard4` (M5).

`Useful links.docx` is disabled: 193 characters of text and a pile of embedded
screenshots — a bookmark list, not a lecture. Same reason as `code/README.md`.
The two `LINKs` files beside it are `.txt`, which is not extracted, so they need
no line here.

## How these were classified

Not by filename. Every one was settled against evidence, in this order:

1. **The author on page 1.** Almost every deck opens with "CA' FOSCARI
   CHALLENGE SCHOOL" and a name, and the timetable says which module that person
   teaches. Minello, Ligorio and De Marinis → M2. Droghetti → M3. Crippa,
   Fioravanti, Onorati and Galatro → M6. Raggi, Fasano and Pesenti → M1.
2. **The module in the header.** The three `2026090x_..._CFCS` decks carry
   "— MODULE 7" in their own title block.
3. **The PDF creation date against the timetable.** Four handwritten files
   carried no text and no author. Their creation dates land on Martina's
   lectures: `whiteboard1` 18 May (M4, Basics of QC, 16 May), `lezione2` 23 May
   (M4, Practice on Quantum Circuits, **same day**), `whiteboard3` 6 June (M4,
   Quantum Generative AI, **same day**), `whiteboard4` 15 June (M5, Tutorial on
   Quantum Generative AI, 13 June).
4. **Imports, for the notebooks.** sklearn/torch/tensorflow and no quantum
   import → M2. The June-30 bundle is one project — `qiskit-ibm-runtime`, a
   README saying "quantum-shor", a report on running Shor on IBM hardware — and
   it goes to M6 whole, with `Shor.pdf` by Galatro, who teaches M6.

## Handwriting: five files, 195 pages

`FCaruso`, `lezione2`, `whiteboard1`, `whiteboard3`, `whiteboard4` have **zero
characters of text** and 335-508 vector strokes per page: lectures written on a
tablet, not scans. OCR cannot read them — tesseract does printed type — and is
switched off for that reason. They are typed `slides`, which forces captioning,
and the vision model reads the words though it gets the formulas wrong. Without
that stage these 195 pages are invisible to search.

## Two sources with no module

The assessment reviews cover modules 4-5-6 and 1-2-3 respectively. A source
carries one module, so neither can be assigned without lying about the other
two. They stay unassigned and remain findable by content — which is what they
are for, since they record what was actually asked.

## Disabled, and why

| path                                 | why                                                                                                           |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| `books/Landau. Lifshitz ...`         | 1,144 pages of graduate theory against a 24-hour introductory module                                          |
| `books/Landau_Lifshitz_T2_short.pdf` | same reason                                                                                                   |
| `slides/deep-learning.pptx`          | same deck as `deep-learning (final version).pptx`: 81 slides and 17,807 characters of text, identical in both |
| `code/README.md`                     | 79 bytes, a title and one line                                                                                |

Flip `enabled` to `true` and the next ingest picks the file up. It is one word.

## Duplicates removed

17 files, 71 MB: browser ` (1)` copies, and root copies of things already
filed. All verified byte-identical before deleting.

Three pairs look identical and are **not** — same title page, different
material, so both are kept: `Slides_master_QML1`/`QML2` (126p/93p, 2 shared
pages), `Lecture4 (spins_and_qubits)`/`lectures_master_spin_qubit` (26p/18p),
`lecture_QM_formalism`/`lectures_formalism1` (17p/11p, nothing shared).

## Not indexed

`.docx`, `.html`, `.txt` are not in `extract.SUPPORTED`, so
`PYTHON_LINK TO MATERIALS.docx`, the two `*_notebook.html` renders and
`requirements.txt` / `parity.txt` sit in their folders and are skipped in
silence. The html files are exports of notebooks that are indexed anyway.

## Module ids

From the course timetable, parsed by `studykb`. `kb_outline M8` prints any of
them lecture by lecture.

| id  | module                               | teachers                                          | sources |
| --- | ------------------------------------ | ------------------------------------------------- | ------- |
| M1  | Preliminaries                        | Corazza, Raggi, Fasano, Pesenti, Bernes           | 9       |
| M2  | Classical Machine Learning           | Minello, Ligorio, Di Matteo, De Marinis, Federici | 39      |
| M3  | Introduction to Quantum Mechanics    | Droghetti                                         | 21      |
| M4  | From Quantum Computing to Quantum AI | Martina, Caruso                                   | 11      |
| M5  | Towards QML applications             | Martina                                           | 8       |
| M6  | Real Quantum Processors              | Crippa, Galatro, Onorati                          | 16      |
| M7  | Quantum Machines Deep Learning       | Zarbo                                             | 10      |
| M8  | Quantum Machine Learning for Finance | Corazza, Fasano, Raggi, De Nobili, Costola        | **0**   |
| M9  | Quantum Applications                 | Fasano, Leone, Ferrara                            | 4       |

**M8 is the only empty module, and it is the 8-CFU one.** Corazza teaches its
first lecture on 12 October. Transcripts are still missing everywhere.

# How to use studykb, step by step

Follow the steps in order. Each one tells you what to run, what you should see,
and what to do if you see something else.

Every command runs from the repo:

```bash
cd ~/Personale/studykb
```

---

## Step 0 — Start the services

The search database (Qdrant) must be running. The server is optional and only
needed for Step 8.

```bash
docker compose up -d qdrant
docker compose --profile serve up -d     # only if you want the MCP server
```

Check:

```bash
docker compose ps
```

**Everything else runs on your machine, not in a container.** The container has
its own state file and its own work directory, so ingesting there and reviewing
here would report every source as "not extracted" — two directories, not a bug.
Pick the host and stay on it.

You also need **ollama running on your machine**, because that is where the
models live. It normally starts with the system. Check:

```bash
curl -s localhost:11434/api/tags > /dev/null && echo "ollama ok"
```

---

## Step 1 — Check that everything is ready

```bash
uv run studykb doctor
```

This checks: the models are downloaded, the database answers, the folders
exist, the configuration is valid.

Expected: every line has a green ✓.

| If you see | It means | Do this |
|---|---|---|
| `✗ embed: bge-m3` | a model is missing | `ollama pull bge-m3` |
| `✗ Qdrant unreachable` | the database is not running | go back to Step 0 |
| `! ocrmypdf missing` | **normal** | ignore it — OCR is switched off, see Step 5 |

Do not go further until `doctor` is clean. A missing model only fails three
stages into a run that has already taken twenty minutes.

---

## Step 2 — Put the material in place

Files go in `~/Personale/QML/kb/`, sorted by what they are. **The folder
decides the type**, and the type decides whether figures get described:

| Folder | What goes in it | Figures described? |
|---|---|---|
| `books/` | textbooks, long reference documents | no |
| `papers/` | papers, lecture notes, exercises | no |
| `slides/` | lecture decks, handwritten lectures (PDF or PowerPoint) | **yes** |
| `code/` | notebooks (`.ipynb`), scripts (`.py`), notes (`.md`) | no |
| `transcripts/` | lecture subtitles (`.vtt`, `.srt`) or the platform's Word exports (`.docx`, `.docm`) | no |

Getting this wrong costs something real: a deck dropped anywhere else is typed
`paper`, and on a deck roughly 40% of the content lives in diagrams that only a
figure description makes findable.

Folders are **flat** — no `M1/`, `M2/` subfolders. A file's path is its
identity, so moving it later creates a second source under the new path while
the old chunks stay behind. The module goes in `MANIFEST.md` instead, where
changing it is editing a line.

`kb/` holds study material **and nothing else**. Paperwork, the thesis code and
the vault live outside it, which is why `corpus.yaml` has an empty `exclude`
list. If that list ever needs to grow again, the root is in the wrong place.

---

## Step 3 — See what would happen, without doing it

```bash
uv run studykb ingest --corpus qml-master --root ~/Personale/QML/kb --dry-run
```

Nothing is written. You get a table of how much work each stage would do, and a
list of files that could not be assigned to a module.

**Check three things:**

1. The number of sources matches what you expect.
2. No file from somewhere else appears in the list.
3. The "sources with no module" list is empty.

If point 3 is not empty, go to Step 4. Otherwise skip to Step 5.

---

## Step 4 — Assign the unassigned files

The dry run prints lines ready to paste, like this:

```
| slides/lecture-corazza.pdf |  |
```

Open `corpora/qml-master/MANIFEST.md` and paste them into the table, filling in
the module:

```
| slides/lecture-corazza.pdf | M8 | slides | |
```

The four columns are: path, module, type, enabled.

- **module** — `M1` to `M9`. The list of modules is at the bottom of the same
  file.
- **type** — leave empty to keep what was detected. Write `slides` to force
  figure captioning.
- **enabled** — write `false` to keep the file out of the index.

If you do not know which module a file belongs to, **leave it empty**. A wrong
module is worse than none: searching that module will silently miss the file.

Run Step 3 again and confirm the list is now empty.

---

## Step 5 — Ingest

```bash
uv run studykb ingest --corpus qml-master --root ~/Personale/QML/kb
```

**Run it whole. Never with `--only`.** Each stage reads what the one above it
wrote, and skipping extraction leaves older files in place for the later stages
to choke on.

This takes time. On the full corpus, roughly 30-40 minutes, most of it the
figure descriptions at about 1.8 seconds a page.

OCR is switched off. The only files that trigger it are lectures handwritten on
a tablet, and `ocrmypdf` reads printed type — worse, its output would be indexed
as `provenance: text-layer`, the most trusted label, so a run would file its
guesses as if they had been read from the file. Turn it back on the day a scan
of *printed* text arrives.

You will see stages go past: `ocr`, `extract`, `asr_cleanup`, `vision`, `embed`.
At the end, a chunk count and a **cost table**: wall time, model calls, tokens
and watt-hours per stage.

```bash
uv run studykb stats --corpus qml-master            # compare against past runs
uv run studykb stats --corpus qml-master --run a1b2 # one run, stage by stage
```

Compare `per item` between runs, never the total: the total rises because the
corpus grew.

**Read the warnings at the bottom:**

| Warning | Meaning |
|---|---|
| `N sources with no module` | back to Step 4 |
| `N sources produced no chunks` | those files are searchable nowhere — see Step 6 |
| `N known sources are missing from disk` | files you deleted or moved. Harmless, but check the folder is mounted |

Running it again costs nothing when nothing changed. Adding ten files costs
those ten files.

---

## Step 6 — Check the result before trusting it

This is the important step. **Never skip it after adding new material.**

```bash
uv run studykb review --corpus qml-master --root ~/Personale/QML/kb
```

It writes five files into `~/Personale/QML/vault/95-review/`.

**Open `SUMMARY.md` first.** It is one screen: five checks and a table.

| Check | What it means when it fails |
|---|---|
| every source is indexed | a file ended up searchable nowhere |
| nothing was lost on the way in | chunks overwrote each other |
| no page with text was dropped | a page's text never made it into the index |
| chunks are worth indexing | too many near-empty fragments |
| captions carry content | figure descriptions are empty or useless |

**If all five are ✅, you are done. Go to Step 7.**

If one fails, open the file that answers it:

| Question | File |
|---|---|
| Did a page lose its text? | `extraction.md` |
| Where does one chunk end and the next begin? | `chunks.md` |
| Is a figure description wrong? | `captions.md` |
| Does search find the right passage? | `retrieval.md` |

Two columns in the table are worth knowing:

- **pages** reads `with-text / total`. `0/137` means a document produced no text
  at all — usually a scan needing OCR, or a deck flattened to images.
- **chunks** shows one number normally. Two numbers mean something was lost.

---

## Step 7 — Search

From the terminal:

```bash
uv run studykb search "Grover algorithm" --module M4 -k 5
```

Options:

| Option | Effect |
|---|---|
| `--module M4` | only that module |
| `--type book` | only books. Also: `slides`, `paper`, `transcript`, `caption` |
| `-k 5` | how many passages to return |

Each result shows where it came from and how it was obtained:

```
[1] Nielsen & Chuang p.72 — Quantum search algorithms
    module=M4 type=book provenance=text-layer score=1.000
```

`p.72` is the **page of the PDF file**, the number you type into a PDF viewer.
It is not the number printed on the page — in a book with front matter the two
differ by about a dozen.

**`provenance` tells you how much to trust the passage:**

| Value | Meaning |
|---|---|
| `text-layer` | read directly from the file. This is the document |
| `ocr` | recognised from a scan. Check anything exact |
| `local-vlm` | a small model **describing a figure**. Not a transcription. Never take a formula from it — open the page |
| `asr` | automatic subtitles. Wording approximate, timestamps exact |
| `asr-corrected` | subtitles repaired by a model. Same caution, plus the model may have changed a term |

---

## Step 8 — Use it with Claude Code

The server is already registered. Check:

```bash
claude mcp list
```

Expected: `studykb: http://127.0.0.1:8077/mcp (HTTP) - ✔ Connected`.

From then on you just ask in plain language. Four tools are available:

| Tool | Answers |
|---|---|
| `kb_search` | find passages about a topic, with their page or timestamp |
| `kb_outline` | the lecture-by-lecture programme of a module |
| `kb_lecture` | what was taught on a given date |
| `kb_sources` | which modules exist and how much material each has |

If it says not connected:

```bash
docker compose --profile serve up -d
curl -s localhost:8077/healthz
```

---

## Adding new material later

Three commands:

```bash
uv run studykb ingest --corpus qml-master --root ~/Personale/QML/kb
uv run studykb review --corpus qml-master --root ~/Personale/QML/kb
# then open vault/95-review/SUMMARY.md
```

Only the new files are processed. Everything already indexed is left alone.

Every ingest rewrites `vault/SOURCES.md`: each file, grouped by module, with its
chunk count and the date it was indexed.

---

## Starting over from zero

When you want to rebuild rather than update — after a big reorganisation, or
because you no longer trust what is in there:

```bash
docker compose up -d qdrant
curl -X DELETE http://localhost:6333/collections/studykb   # the index
rm -rf .cache/state-qml-master.db .cache/work              # what has been done
rm -rf ~/Personale/QML/vault/90-extracted                  # the text mirror
rm -rf ~/Personale/QML/vault/00-syllabus                   # regenerated
```

Then Step 3 onwards.

**Check `00-syllabus/` before deleting it.** studykb writes the top of each
module page and keeps whatever sits under the `## Notes` heading, so that is
where your own notes go and they do not come back. `20-thesis/` is never
touched by anything here.

---

## Testing something without touching the real index

There is a separate corpus for trying things out. It writes to its own database
and its own folders, so nothing you do there can damage the real one.

```bash
cp <some-file>.pdf ~/Personale/QML/test-corpus/slides/
uv run studykb ingest --corpus test
uv run studykb review --corpus test
# reports in ~/Personale/QML/test-corpus/vault/95-review/
```

---

## Quick troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `Qdrant unreachable` | database not running | `docker compose up -d` |
| `✗ <model name>` in doctor | model not downloaded | `ollama pull <name>` |
| A file is not found by search | wrong module, or not ingested | check `MANIFEST.md`, then Step 3 |
| Search returns nothing at all | index empty | `uv run studykb doctor` shows the chunk count |
| Ingest seems stuck | figure captioning is slow | normal: seconds per page. Check the GPU with `nvidia-smi` |
| A change to settings had no effect | that stage was not re-run | settings changes trigger a re-run automatically; **code changes do not** |
| A corrected module in `MANIFEST.md` had no effect | — | it does now: that one source re-indexes on the next ingest |
| `Unit() got an unexpected keyword argument` | you ran `--only` and older extracted files are still there | run the ingest whole |

---

## The one rule

**A passage you have not opened is a passage you have not verified.**

The whole system is built so that every claim carries a page number or a
timestamp. That only has value if you use it. Before relying on anything
generated from this material, open two or three of the references and confirm
the text is really there.

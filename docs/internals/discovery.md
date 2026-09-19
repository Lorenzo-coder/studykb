# Discovery

`src/studykb/pipeline.py::discover` and helpers

Turns a corpus root full of files into a list of `Source` objects, each with a
type and a module. Everything downstream works from that list.

## The four steps

```
corpus.root
   │
   ├─ 1. glob      each rule in corpus.yaml, in order; first rule to claim a file wins
   ├─ 2. exclude   fnmatch against corpus.exclude
   ├─ 3. override  MANIFEST.md can change the module, change the type, or drop the file
   └─ 4. assign    module_rules: path regex → calendar date → manifest
```

### 1. Globs, in order

```yaml
sources:
  - glob: "slides/**/*.pdf"
    type: slides
    vision: force
  - glob: "**/*.pdf"        # catch-all, last
    type: paper
    vision: never
```

Order matters: `found` is a dict keyed by the relative path, and a file already
claimed by an earlier rule is skipped. So specific folders win over the
catch-all, and material downloaded next week is picked up without editing
anything.

### 2. Exclusions

`_excluded(rel, patterns)` uses **fnmatch, not `Path.glob`**. This is not a
style choice: pathlib's `**` expands to directories only and never to files, so
`test-corpus/**` excluded nothing at all and the review set was being indexed as
course material. With fnmatch, `*` crosses separators, so `admin/**` covers
everything beneath `admin/`.

The consequence to know about: `*.pdf` in an exclude list also matches
`Book/x.pdf`. The patterns in a manifest are written deliberately, so this is
usually what you want, but it is not glob semantics.

### 3. Manifest overrides

`_read_manifest` parses a markdown table — `| path | module | type | enabled |`.
Header rows and separator rows are skipped by shape, so the file stays readable
as documentation.

An override can change the **type**, not just the module. A file reclassified as
`slides` also gets `vision: force`, because an override that only half applies
is worse than none.

### 4. Module assignment

`_module_for` walks `module_rules` in order and takes the first hit:

| rule | how |
|---|---|
| `path_regex` with a `module` group | `/M7/` or `M7_lecture.pdf` → `M7` |
| `path_regex` with a `date` group and `resolve: calendar_date` | `2026-10-12` → the module teaching that day, from the timetable |
| `manifest` | whatever `MANIFEST.md` says |

Anything left unassigned is **reported, not guessed**: `ingest` prints the list
ready to paste into `MANIFEST.md`. A wrong module is worse than no module,
because `kb_search -m M8` then quietly misses the thing you needed.

## Gate

```bash
uv run studykb ingest --corpus <name> --dry-run
```

Three things to check: the source count, that nothing from another corpus or
from `review/` appears, and that the unassigned list is empty or expected.

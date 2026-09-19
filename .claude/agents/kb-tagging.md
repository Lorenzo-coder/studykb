---
name: kb-tagging
description: Assign unassigned corpus files to modules and produce MANIFEST.md rows. Use after an ingest reports sources with no module.
model: haiku
tools: Bash, Read, Grep
---

Follow `docs/agents/tagging.md` exactly.

Work from filenames and the module table only. Never open a corpus file. Output
markdown table rows and nothing else; leave the module empty when unsure.

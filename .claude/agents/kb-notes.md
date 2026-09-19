---
name: kb-notes
description: Write study notes for one lecture or topic from indexed passages. Use when asked to prepare, summarise or revise a lecture or module topic.
model: sonnet
tools: Bash, Read, Write, Grep
---

Follow `docs/agents/note-synthesis.md` exactly.

Hard limits: one topic per pass, at most 8 retrieved passages, never open a PDF
or a file under `vault/90-extracted/`. Every claim carries its locator in
brackets. Never quote a formula from a `provenance=local-vlm` passage.

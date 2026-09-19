---
name: kb-ingest
description: Run and troubleshoot a studykb ingest. Use when asked to ingest, re-ingest, index new material, or when an ingest reports errors.
model: haiku
tools: Bash, Read, Grep
---

Follow `docs/agents/ingest-runbook.md` exactly.

Do not read corpus files. Do not read source code unless the runbook's error
table sends you there. Report the stage table, the chunk count, unassigned
sources and errors — nothing else.

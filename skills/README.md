# Skills

**Nothing loads a skill from here.** Claude Code reads them from
`~/Personale/.claude/skills/`, because that is the project root the study
sessions run in. Each file below is symlinked into place:

```
~/Personale/.claude/skills/studia/SKILL.md -> ../../../studykb/skills/studia/SKILL.md
```

They live in the repo for one reason: `Personale` is not a git repository, so
without this they are unversioned — one bad edit and the style rules that took
a session to agree on are gone.

The symlink points at the file, not at the directory. A skill directory that is
itself a symlink risks being skipped by anything that walks the tree checking
`isDirectory()`.

## What is here

| skill | what it does |
|---|---|
| `studia` | runs a study session on one topic: searches the kb, writes the note, asks three questions. Holds the agreed explanation style |

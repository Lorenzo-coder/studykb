"""Prompt templates, loaded from ``prompts/*.j2``.

Prompts live in files, not in string literals: changing how slides are captioned
or how notes are phrased is a diffable edit with its own fingerprint, so it
reruns exactly the stage it affects and nothing else.
"""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

from .config import REPO_ROOT

PROMPT_DIR = Path(os.environ.get("STUDYKB_PROMPTS", REPO_ROOT / "prompts"))


class Prompts:
    def __init__(self, directory: Path | None = None):
        self.dir = directory or PROMPT_DIR
        self.env = Environment(
            loader=FileSystemLoader(self.dir),
            autoescape=select_autoescape(default=False),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def get(self, name: str) -> Template:
        return self.env.get_template(f"{name}.j2")

    @lru_cache(maxsize=1)  # noqa: B019 - one instance per process, bounded
    def version(self) -> str:
        """Fingerprint of all prompts, so an edit invalidates the right stage."""
        h = hashlib.sha256()
        for path in sorted(self.dir.glob("*.j2")):
            h.update(path.name.encode())
            h.update(path.read_bytes())
        return h.hexdigest()[:12]

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

_ENV = Environment(
    loader=FileSystemLoader(PROMPT_DIR),
    autoescape=select_autoescape(default=False),
    trim_blocks=True,
    lstrip_blocks=True,
)


def get(name: str) -> Template:
    return _ENV.get_template(f"{name}.j2")


@lru_cache(maxsize=1)
def version() -> str:
    """Fingerprint of all prompts, so an edit invalidates the right stage."""
    h = hashlib.sha256()
    for path in sorted(PROMPT_DIR.glob("*.j2")):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()[:12]

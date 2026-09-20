"""Configuration loading and validation.

Two layers, both data, never code:

* ``config/default.yaml`` (+ optional ``config/local.yaml``, + ``STUDYKB__*``
  env vars) describe *how* to index: models, thresholds, storage.
* ``corpora/<domain>/corpus.yaml`` describes *what* to index: globs, module
  rules, calendar. Swapping this file is what makes studykb reusable.

Everything is validated on startup so a typo in YAML fails loudly at `doctor`
time instead of halfway through a four-hour ingest.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_PREFIX = "STUDYKB__"


# --------------------------------------------------------------------------
# config/default.yaml
# --------------------------------------------------------------------------
class EmbedModel(BaseModel):
    name: str
    dim: int = Field(gt=0)
    batch: int = Field(default=32, gt=0)


class VlmModel(BaseModel):
    name: str
    fallback: str | None = None
    max_long_side_px: int = Field(default=1280, gt=0)


class LlmModel(BaseModel):
    name: str
    num_ctx: int = Field(default=16384, gt=0)
    temperature: float = 0.2


class Models(BaseModel):
    embed: EmbedModel
    vlm: VlmModel
    llm: LlmModel


class Storage(BaseModel):
    qdrant_url: str
    collection: str
    state_db: Path
    vault: Path


class OcrCfg(BaseModel):
    enabled: bool = True
    trigger_chars_per_page: int = 120
    cmd: list[str]
    timeout_s: int = 1800


class VisionCfg(BaseModel):
    enabled: bool = True
    trigger_chars_per_page: int = 250
    min_graphics: int = 12
    render_dpi: int = 150


class ExtractCfg(BaseModel):
    ocr: OcrCfg
    vision: VisionCfg


class TranscriptCfg(BaseModel):
    window_seconds: int = Field(default=300, gt=0)
    asr_cleanup: bool = True


class ChunkCfg(BaseModel):
    target_tokens: int = Field(default=800, gt=0)
    overlap_tokens: int = Field(default=120, ge=0)
    split_on: Literal["headings", "none"] = "headings"


class RetrievalCfg(BaseModel):
    hybrid: bool = True
    k_dense: int = 30
    k_lexical: int = 30
    k_final: int = 8


class Config(BaseModel):
    llm_endpoint: str
    llm_api_key: str = "ollama"
    models: Models
    storage: Storage
    extract: ExtractCfg
    transcript: TranscriptCfg
    chunk: ChunkCfg
    retrieval: RetrievalCfg

    @property
    def work(self) -> Path:
        """Per-stage scratch output, beside the state db so the two move together."""
        return self.storage.state_db.parent / "work"

    def fingerprint(self, prompt_version: str = "") -> dict[str, str]:
        """Per-stage fingerprints over everything that stage consumes.

        A stage reruns only when *its own* inputs changed: editing the vision
        threshold or the caption prompt must not invalidate embeddings that cost
        an hour to build. The prompt fingerprint is folded into the two stages
        that actually send a prompt.
        """
        m = self.models
        return {
            # Config changes invalidate a stage automatically; code changes do
            # not. Bump these when the extraction or OCR *logic* changes, or the
            # next run will happily keep last week's wrong output.
            "ocr": _hash_obj({"cfg": self.extract.ocr, "code": "v2"}),
            # v4: Unit lost `has_images`, so units written by v3 no longer load.
            "extract": "v4",
            "asr_cleanup": _hash_obj(
                {
                    "on": self.transcript.asr_cleanup,
                    "w": self.transcript.window_seconds,
                    "m": m.llm.name,
                    "p": prompt_version,
                }
            ),
            "vision": _hash_obj({"cfg": self.extract.vision, "m": m.vlm.name, "p": prompt_version}),
            "chunk": _hash_obj(self.chunk),
            "embed": _hash_obj(
                {"m": m.embed.name, "d": m.embed.dim, "chunk": _hash_obj(self.chunk), "code": "v2"}
            ),
        }


def _hash_obj(obj: Any) -> str:
    import hashlib
    import json

    if isinstance(obj, BaseModel):
        obj = obj.model_dump(mode="json")
    blob = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


# --------------------------------------------------------------------------
# corpora/<domain>/corpus.yaml
# --------------------------------------------------------------------------
class CalendarCfg(BaseModel):
    source: str
    sheet: str | None = None
    columns: dict[str, str] = Field(default_factory=dict)


class SourceRule(BaseModel):
    glob: str
    type: Literal["book", "slides", "paper", "transcript"]
    vision: Literal["auto", "force", "never"] = "auto"
    enabled: bool = True


class ModuleRule(BaseModel):
    match: Literal["path_regex"]
    pattern: str | None = None
    resolve: Literal["direct", "calendar_date"] = "direct"


class Corpus(BaseModel):
    domain: str
    title: str = ""
    root: Path
    # Override storage.collection and storage.vault. A test corpus must write
    # its index and its extractions somewhere the real ones cannot be damaged
    # by it — a review run must never leave files in the study vault.
    collection: str | None = None
    vault: Path | None = None
    calendar: CalendarCfg | None = None
    sources: list[SourceRule]
    # Globs skipped whatever the source rules say. Admin paperwork lives in the
    # same folders as the study material and would otherwise pollute retrieval.
    exclude: list[str] = Field(default_factory=list)
    module_rules: list[ModuleRule] = Field(default_factory=list)
    glossary: list[str] = Field(default_factory=list)

    # Where this manifest was loaded from, so MANIFEST.md sits next to it.
    manifest_dir: Path = Path(".")

    @field_validator("sources")
    @classmethod
    def _at_least_one(cls, v: list[SourceRule]) -> list[SourceRule]:
        if not any(s.enabled for s in v):
            raise ValueError("corpus.yaml declares no enabled sources")
        return v


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------
def _deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _env_overrides() -> dict:
    """STUDYKB__MODELS__LLM__NAME=foo -> {'models': {'llm': {'name': 'foo'}}}."""
    out: dict = {}
    for key, raw in os.environ.items():
        if not key.startswith(ENV_PREFIX):
            continue
        cursor = out
        parts = key[len(ENV_PREFIX) :].lower().split("__")
        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = yaml.safe_load(raw)
    return out


def load_config(path: Path | None = None) -> Config:
    path = path or Path(os.environ.get("STUDYKB_CONFIG", REPO_ROOT / "config/default.yaml"))
    data = yaml.safe_load(path.read_text())
    local = path.parent / "local.yaml"
    if local.exists():
        data = _deep_merge(data, yaml.safe_load(local.read_text()) or {})
    return Config(**_deep_merge(data, _env_overrides()))


def load_corpus(domain_or_path: str | Path) -> Corpus:
    path = Path(domain_or_path)
    if not path.suffix:
        path = REPO_ROOT / "corpora" / str(domain_or_path) / "corpus.yaml"
    if not path.exists():
        raise FileNotFoundError(f"no corpus manifest at {path}")
    data = yaml.safe_load(path.read_text())
    return Corpus(**data, manifest_dir=path.parent)

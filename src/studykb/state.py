"""Incremental-ingest bookkeeping.

The corpus grows every week, so a full reprocess is never acceptable. Every
(source, stage) pair records the source checksum and the fingerprint of the
config that produced its output. A stage reruns only when one of the two
changed, which means:

* adding 40 PDFs costs those 40 PDFs;
* editing ``caption_slide.j2`` reruns vision and nothing else;
* rerunning with nothing changed does no work at all.

Chunk IDs are derived deterministically from (source, locator, index) so a
re-index upserts over the previous rows instead of duplicating them.
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
import uuid
from contextlib import closing
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS stage_state (
    source      TEXT NOT NULL,          -- path relative to the corpus root
    stage       TEXT NOT NULL,
    source_sha  TEXT NOT NULL,
    cfg_fp      TEXT NOT NULL,
    output_ref  TEXT,
    done_at     REAL NOT NULL,
    PRIMARY KEY (source, stage)
);
CREATE TABLE IF NOT EXISTS seen_sources (
    source      TEXT PRIMARY KEY,
    source_sha  TEXT NOT NULL,
    type        TEXT NOT NULL,
    module      TEXT,
    last_seen   REAL NOT NULL
);
"""

# Namespace for deterministic chunk ids. Constant on purpose: changing it would
# orphan every previously indexed point.
_CHUNK_NS = uuid.UUID("6f1b9a2e-3c44-4f0d-9a7e-8b5d2c1f0e33")


def file_sha(path: Path, _bufsize: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(_bufsize):
            h.update(block)
    return h.hexdigest()


def chunk_id(source: str, locator: str, index: int) -> str:
    """Stable UUID for a chunk. Same inputs always yield the same point id."""
    return str(uuid.uuid5(_CHUNK_NS, f"{source}|{locator}|{index}"))


class State:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> State:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- stage gating ------------------------------------------------------
    def needs(self, source: str, stage: str, source_sha: str, cfg_fp: str) -> bool:
        row = self.conn.execute(
            "SELECT source_sha, cfg_fp FROM stage_state WHERE source = ? AND stage = ?",
            (source, stage),
        ).fetchone()
        return row is None or row[0] != source_sha or row[1] != cfg_fp

    def mark(self, source: str, stage: str, source_sha: str, cfg_fp: str, output_ref: str | None = None) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO stage_state VALUES (?, ?, ?, ?, ?, ?)",
            (source, stage, source_sha, cfg_fp, output_ref, time.time()),
        )
        self.conn.commit()

    def output_ref(self, source: str, stage: str) -> str | None:
        row = self.conn.execute(
            "SELECT output_ref FROM stage_state WHERE source = ? AND stage = ?", (source, stage)
        ).fetchone()
        return row[0] if row else None

    # -- source inventory --------------------------------------------------
    def see(self, source: str, source_sha: str, type_: str, module: str | None) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO seen_sources VALUES (?, ?, ?, ?, ?)",
            (source, source_sha, type_, module, time.time()),
        )
        self.conn.commit()

    def vanished(self, present: set[str]) -> list[str]:
        """Sources recorded previously but no longer on disk.

        Returned rather than acted upon: dropping their chunks is the caller's
        call, because an unmounted volume looks exactly like a deletion.
        """
        known = {r[0] for r in self.conn.execute("SELECT source FROM seen_sources")}
        return sorted(known - present)

    def forget(self, source: str) -> None:
        with closing(self.conn.cursor()) as cur:
            cur.execute("DELETE FROM stage_state WHERE source = ?", (source,))
            cur.execute("DELETE FROM seen_sources WHERE source = ?", (source,))
        self.conn.commit()

    def clear_stage(self, stage: str) -> int:
        """Forget every record of one stage. Returns how many were dropped."""
        cur = self.conn.execute("DELETE FROM stage_state WHERE stage = ?", (stage,))
        self.conn.commit()
        return cur.rowcount

    def inventory(self) -> list[tuple[str, str, str | None]]:
        return list(
            self.conn.execute("SELECT source, type, module FROM seen_sources ORDER BY module, source")
        )

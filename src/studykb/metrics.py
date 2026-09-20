"""What a run cost, recorded per stage.

A run of this pipeline is measured in tens of minutes of GPU time, and the only
way to know whether a change made it cheaper — a different embedder, a higher
graphics floor, a shorter prompt — is to have measured the run before it. So
every stage writes one row, into the same SQLite file that already drives
incremental ingestion. No new dependency, no service, and the history survives
because it lives beside the state it describes.

Three things are recorded, in descending order of how much they are worth:

* **wall time and throughput per stage**, which is what tells you whether to
  start a run before lunch or before bed;
* **model calls and tokens**, read from the `usage` block every
  OpenAI-compatible endpoint returns, so a stage's cost is attributable even
  when it is fast;
* **energy**, integrated from `nvidia-smi` power readings while the stage runs.

The energy figure is honest about what it is: **whole-GPU draw**, not this
process's share. Nothing else should be using the card during an ingest, but if
something is, the number is an upper bound. Where `nvidia-smi` is missing the
columns are simply null and everything else still works.
"""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id      TEXT NOT NULL,
    stage       TEXT NOT NULL,
    corpus      TEXT NOT NULL,
    started     REAL NOT NULL,
    seconds     REAL NOT NULL,
    sources     INTEGER NOT NULL DEFAULT 0,
    items       INTEGER NOT NULL DEFAULT 0,   -- pages, captions or chunks, by stage
    llm_calls   INTEGER NOT NULL DEFAULT 0,
    llm_seconds REAL    NOT NULL DEFAULT 0,
    tokens_in   INTEGER NOT NULL DEFAULT 0,
    tokens_out  INTEGER NOT NULL DEFAULT 0,
    gpu_wh      REAL,                         -- null where nvidia-smi is absent
    gpu_peak_w  REAL,
    errors      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (run_id, stage)
);
"""

SAMPLE_SECONDS = 2.0


# --------------------------------------------------------------------------
# GPU power
# --------------------------------------------------------------------------
class GpuPower:
    """Integrates whole-GPU watts into watt-hours while a stage runs.

    A sample costs ~25 ms and one is taken every two seconds, so the meter
    itself is about 1% of one core. Sampling rather than a start/end reading is
    the point: a stage that loads a model, works for eight minutes and idles is
    not described by either endpoint.
    """

    def __init__(self, interval: float = SAMPLE_SECONDS):
        self.available = shutil.which("nvidia-smi") is not None
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.wh = 0.0
        self.peak_w = 0.0
        self.samples = 0

    @staticmethod
    def _watts() -> float | None:
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            return float(out.stdout.strip().splitlines()[0])
        except Exception:  # noqa: BLE001 - telemetry must never fail a run
            return None

    def _loop(self) -> None:
        last = time.time()
        while not self._stop.wait(self.interval):
            now = time.time()
            w = self._watts()
            if w is not None:
                self.wh += w * (now - last) / 3600.0
                self.peak_w = max(self.peak_w, w)
                self.samples += 1
            last = now

    def start(self) -> None:
        if not self.available:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._thread:
            self._stop.set()
            self._thread.join(timeout=self.interval + 5)


# --------------------------------------------------------------------------
# One row per stage
# --------------------------------------------------------------------------
@dataclass
class StageMetrics:
    stage: str
    started: float = 0.0
    seconds: float = 0.0
    sources: int = 0
    items: int = 0
    llm_calls: int = 0
    llm_seconds: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    gpu_wh: float | None = None
    gpu_peak_w: float | None = None
    errors: int = 0

    @property
    def per_item(self) -> float:
        return self.seconds / self.items if self.items else 0.0


@dataclass
class Run:
    """Collects one row per stage and writes them when the run ends."""

    corpus: str
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    stages: list[StageMetrics] = field(default_factory=list)

    @contextmanager
    def stage(self, name: str, llm=None):
        """Time one stage, and attribute to it whatever the LLM did meanwhile."""
        m = StageMetrics(stage=name, started=time.time())
        before = llm.counters() if llm is not None else None
        power = GpuPower()
        power.start()
        t0 = time.perf_counter()
        try:
            yield m
        finally:
            m.seconds = time.perf_counter() - t0
            power.stop()
            if power.samples:
                m.gpu_wh, m.gpu_peak_w = power.wh, power.peak_w
            if before is not None:
                after = llm.counters()
                m.llm_calls = after["calls"] - before["calls"]
                m.llm_seconds = after["seconds"] - before["seconds"]
                m.tokens_in = after["tokens_in"] - before["tokens_in"]
                m.tokens_out = after["tokens_out"] - before["tokens_out"]
            self.stages.append(m)

    def save(self, conn: sqlite3.Connection) -> None:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (self.run_id, m.stage, self.corpus, m.started, m.seconds, m.sources,
                 m.items, m.llm_calls, m.llm_seconds, m.tokens_in, m.tokens_out,
                 m.gpu_wh, m.gpu_peak_w, m.errors)
                for m in self.stages
            ],
        )
        conn.commit()


def history(conn: sqlite3.Connection, limit: int = 10) -> list[tuple]:
    """Past runs, newest first: one row per run with its stages folded in."""
    conn.executescript(SCHEMA)
    return list(
        conn.execute(
            """
            SELECT run_id, corpus, MIN(started), SUM(seconds), SUM(items),
                   SUM(llm_calls), SUM(tokens_in), SUM(tokens_out),
                   SUM(gpu_wh), MAX(gpu_peak_w), SUM(errors)
            FROM runs GROUP BY run_id, corpus
            ORDER BY MIN(started) DESC LIMIT ?
            """,
            (limit,),
        )
    )


def stages_of(conn: sqlite3.Connection, run_id: str) -> list[tuple]:
    conn.executescript(SCHEMA)
    return list(
        conn.execute(
            """SELECT stage, seconds, sources, items, llm_calls, llm_seconds,
                      tokens_in, tokens_out, gpu_wh, gpu_peak_w, errors
               FROM runs WHERE run_id = ? ORDER BY started""",
            (run_id,),
        )
    )

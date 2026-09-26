"""One OpenAI-compatible client for every model role.

ollama, LM Studio, vLLM and the hosted APIs all speak this protocol, so a single
httpx client covers all of them and switching backend is a URL in config. There
is deliberately no provider abstraction layer.

VRAM note: on an 8 GB card the embedder, the VLM and the text model cannot be
resident at once. Callers run one stage at a time, and ``unload`` evicts the
previous model before the next stage loads its own.
"""

from __future__ import annotations

import base64
import re
import time
from pathlib import Path

import httpx

from .config import Config


class LLM:
    def __init__(self, cfg: Config, timeout: float = 600.0):
        self.cfg = cfg
        self.base = cfg.llm_endpoint.rstrip("/")
        # Every model call in the system goes through _post, so counting there
        # covers embeddings, captions and ASR cleanup without touching any of
        # them. metrics.Run reads these as a before/after pair per stage.
        self._calls = 0
        self._seconds = 0.0
        self._tokens_in = 0
        self._tokens_out = 0
        self.client = httpx.Client(
            base_url=self.base,
            timeout=timeout,
            headers={"Authorization": f"Bearer {cfg.llm_api_key}"},
        )

    def counters(self) -> dict:
        return {"calls": self._calls, "seconds": self._seconds,
                "tokens_in": self._tokens_in, "tokens_out": self._tokens_out}

    def _post(self, path: str, payload: dict) -> dict:
        """The one place a model is called, so the one place worth measuring."""
        t0 = time.perf_counter()
        try:
            r = self.client.post(path, json=payload)
            r.raise_for_status()
            data = r.json()
        finally:
            # Counted even when it raises: a call that failed still cost the
            # time it burned, and a stage that fails slowly is worth seeing.
            self._seconds += time.perf_counter() - t0
            self._calls += 1
        usage = data.get("usage") or {}
        self._tokens_in += usage.get("prompt_tokens", 0)
        self._tokens_out += usage.get("completion_tokens", 0)
        return data

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> LLM:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- embeddings --------------------------------------------------------
    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        m = self.cfg.models.embed
        out: list[list[float]] = []
        for i in range(0, len(texts), m.batch):
            batch = texts[i : i + m.batch]
            body = self._post("/embeddings", {"model": m.name, "input": batch})
            data = sorted(body["data"], key=lambda d: d["index"])
            out.extend(d["embedding"] for d in data)
        for vec in out:
            if len(vec) != m.dim:
                raise ValueError(
                    f"{m.name} returned dim {len(vec)}, config says {m.dim}. "
                    f"Fix models.embed.dim and reindex — a mismatch silently poisons search."
                )
        return out

    # -- text --------------------------------------------------------------
    def complete(self, prompt: str, *, system: str | None = None, model: str | None = None) -> str:
        msgs = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        return self._chat(model or self.cfg.models.llm.name, msgs)

    # -- vision ------------------------------------------------------------
    def describe_image(self, image: Path, prompt: str, *, model: str | None = None) -> str:
        b64 = base64.b64encode(image.read_bytes()).decode()
        msgs = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            }
        ]
        vlm = self.cfg.models.vlm
        try:
            return self._chat(model or vlm.name, msgs)
        except (httpx.HTTPError, ValueError):
            # The 7B VLM is the tightest fit on 8 GB; a dense slide can still OOM
            # it. The 2B document model always fits, so a page gets a weaker
            # caption instead of no caption.
            if vlm.fallback and (model or vlm.name) != vlm.fallback:
                return self._chat(vlm.fallback, msgs)
            raise

    # -- plumbing ----------------------------------------------------------
    def _chat(self, model: str, messages: list[dict]) -> str:
        body = self._post(
            "/chat/completions",
            {
                "model": model,
                "messages": messages,
                "temperature": self.cfg.models.llm.temperature,
                "max_tokens": self.cfg.models.llm.num_ctx // 2,
            },
        )
        return body["choices"][0]["message"]["content"].strip()

    def unload(self, model: str) -> None:
        """Evict a model from VRAM so the next stage has room.

        ollama-specific (`keep_alive: 0` on the native endpoint). Other backends
        manage their own memory, so failure here is not an error.
        """
        native = self.base.removesuffix("/v1") + "/api/generate"
        try:
            httpx.post(native, json={"model": model, "keep_alive": 0}, timeout=30.0)
        except httpx.HTTPError:
            pass

    def available_models(self) -> set[str]:
        r = self.client.get("/models")
        r.raise_for_status()
        return {m["id"] for m in r.json().get("data", [])}


def strip_thinking(text: str) -> str:
    """qwen3 reasons in <think> blocks; notes must not inherit them.

    It also ends some answers with a bare ``/think`` switch, 89 times in one run.
    """
    text = text.rsplit("</think>", 1)[-1] if "</think>" in text else text
    return re.sub(r"\s*/(no_)?think\s*$", "", text.strip())

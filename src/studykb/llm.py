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
import json
from pathlib import Path

import httpx

from .config import Config


class LLM:
    def __init__(self, cfg: Config, timeout: float = 600.0):
        self.cfg = cfg
        self.base = cfg.llm_endpoint.rstrip("/")
        self.client = httpx.Client(
            base_url=self.base,
            timeout=timeout,
            headers={"Authorization": f"Bearer {cfg.llm_api_key}"},
        )

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
            r = self.client.post("/embeddings", json={"model": m.name, "input": batch})
            r.raise_for_status()
            data = sorted(r.json()["data"], key=lambda d: d["index"])
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
        r = self.client.post(
            "/chat/completions",
            json={
                "model": model,
                "messages": messages,
                "temperature": self.cfg.models.llm.temperature,
                "max_tokens": self.cfg.models.llm.num_ctx // 2,
            },
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

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


def parse_json_response(text: str) -> object:
    """Pull JSON out of a local model's answer.

    Small models wrap JSON in prose or fences however they feel, and qwen3 emits
    <think> blocks. Strip all of it before parsing.
    """
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    start = min((i for i in (text.find("{"), text.find("[")) if i != -1), default=-1)
    if start == -1:
        raise ValueError(f"no JSON in model response: {text[:200]!r}")
    end = max(text.rfind("}"), text.rfind("]"))
    return json.loads(text[start : end + 1])


def strip_thinking(text: str) -> str:
    """qwen3 reasons in <think> blocks; notes must not inherit them."""
    return text.rsplit("</think>", 1)[-1].strip() if "</think>" in text else text.strip()

# uv provides the interpreter and the resolver; no pip anywhere in this image.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# tesseract + ocrmypdf for PDFs that arrive without a text layer, poppler for
# the page rendering the vision stage needs. ita+eng: the course is in English
# but parts of the material (regulation, translated textbooks) are Italian.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ocrmypdf \
        tesseract-ocr tesseract-ocr-eng tesseract-ocr-ita \
        ghostscript poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Dependencies first so a source edit does not re-resolve the environment.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY src/ ./src/
COPY config/ ./config/
COPY prompts/ ./prompts/
COPY corpora/ ./corpora/
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["studykb"]
CMD ["--help"]

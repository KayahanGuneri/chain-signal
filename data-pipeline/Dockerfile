FROM python:3.12-slim AS test

WORKDIR /app

COPY pyproject.toml .
COPY src ./src
COPY tests ./tests

RUN python -m pip install --no-cache-dir ".[dev]"

RUN python -m pytest -q
RUN python -m ruff check src tests
RUN python -m ruff format --check src tests
RUN python -m mypy src tests

RUN touch /tmp/quality-gate-passed


FROM python:3.12-slim AS runtime

WORKDIR /app

COPY pyproject.toml .
COPY src ./src

RUN python -m pip install --no-cache-dir .

COPY --from=test /tmp/quality-gate-passed /tmp/quality-gate-passed

CMD ["python", "-m", "chainsignal_pipeline"]

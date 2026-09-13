FROM python:3.12-slim
WORKDIR /app

COPY pyproject.toml .
COPY src ./src
COPY tests ./tests

RUN python -m pip install --no-cache-dir .
RUN python -m unittest discover -s tests -v

CMD ["python", "-m", "chainsignal_pipeline"]
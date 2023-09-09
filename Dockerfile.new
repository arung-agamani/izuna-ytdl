FROM python:3.11

RUN apt-get update && apt-get install -y ffmpeg
RUN pip install poetry==1.6.1

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN touch README.md
RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

COPY izuna_ytdl ./izuna_ytdl
COPY alembic ./alembic
COPY script ./script
COPY tests ./tests
RUN poetry install --without dev

EXPOSE 8000
ENTRYPOINT [ "poetry", "run", "uvicorn", "izuna_ytdl.main:app", "--host=0.0.0.0", "--port=8000"]

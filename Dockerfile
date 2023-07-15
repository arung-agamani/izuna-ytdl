FROM arung-agamani/ytdl-base:1.0

RUN mkdir /app

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN touch README.md
RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR
COPY izuna_ytdl ./izuna_ytdl
RUN poetry install --without dev

EXPOSE 5000
# TODO: Actually use WSGI server rather than flask cli
ENTRYPOINT [ "poetry", "run", "flask", "--app", "./izuna_ytdl/main.py", "run", "--host=0.0.0.0" ]
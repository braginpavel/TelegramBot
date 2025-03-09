FROM python:3.11
ENV PYTHONBUFFERED True
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache
WORKDIR /app

# Environment variables
ENV HOST_NAME="host.docker.internal"

# Install requirements
COPY pyproject.toml Makefile ./

RUN make install-poetry
ENV PATH="/root/.local/bin:$PATH"
RUN make install-deps

COPY src/ ./src

WORKDIR /app
ENV PYTHONPATH="${PYTHONPATH}: app/"

# Run server
EXPOSE 8080

RUN nohup make run-app &

ENTRYPOINT poetry run python -m http.server 8080
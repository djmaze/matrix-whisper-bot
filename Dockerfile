FROM python:3.10

RUN apt-get update \
 && apt install -y libolm-dev \
 && apt-get clean \
 && rm /var/lib/apt/lists/* -fR

# Configure Poetry
ENV POETRY_VERSION=1.4.0
ENV POETRY_VENV=/opt/poetry-venv

# Install poetry separated from system interpreter
RUN python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION}

# Add `poetry` to PATH
ENV PATH="${PATH}:${POETRY_VENV}/bin"

ARG APP_USER_ID=1000 APP_GROUP_ID=1000
RUN groupadd app -g ${APP_GROUP_ID} -r && useradd -u ${APP_USER_ID} -r -g app -m -s /bin/bash app

USER app
WORKDIR /app

# Install dependencies
COPY poetry.lock pyproject.toml ./
RUN poetry install --no-cache

CMD ["poetry", "run", "python", "-u", "src/main.py"]

COPY src ./src

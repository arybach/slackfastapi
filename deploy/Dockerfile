FROM python:3.10.8-slim-buster
RUN apt-get update \
  && apt-get install -y gcc \
  && apt-get install -y ffmpeg libsm6 libxext6 \
  && rm -rf /var/lib/apt/lists/*

RUN pip install poetry==1.7.1

# Configuring poetry
RUN poetry config virtualenvs.create false

# Copying requirements of a project
COPY pyproject.toml poetry.lock /app/src/
WORKDIR /app/src

# Installing requirements
RUN poetry install
# Removing gcc
RUN apt-get purge -y \
  gcc \
  && rm -rf /var/lib/apt/lists/*

# Copying actuall application
COPY . /app/src/
RUN poetry install

# Declare arguments
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY

ARG RABBITMQ_USER
ARG RABBITMQ_PASSWORD

ARG SLACK_FASTAPI_DB_USER
ARG SLACK_FASTAPI_DB_PASS

ARG POSTGRES_USER
ARG POSTGRES_PASSWORD

# Set AWS credentials as environment variables
ENV AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ENV AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}

ENV RABBITMQ_USER=${RABBITMQ_USER}
ENV RABBITMQ_PASSWORD=${RABBITMQ_PASSWORD}

ENV SLACK_FASTAPI_DB_USER=${SLACK_FASTAPI_DB_USER}
ENV SLACK_FASTAPI_DB_PASS=${SLACK_FASTAPI_DB_PASS}

ENV POSTGRES_USER=${POSTGRES_USER}
ENV POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

# Install AWS CLI
RUN apt-get update && apt-get install -y awscli && rm -rf /var/lib/apt/lists/*

# Download models from S3
RUN aws s3 cp s3://slackfastapi-backend/trained_models/ /app/src/trained_models --recursive

CMD ["/usr/local/bin/python", "-m", "slack_fastapi"]

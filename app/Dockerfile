FROM python:3.12.7-slim

ENV GITLEAKS_VERSION=8.18.2
ENV GITLEAKS_URL=https://github.com/zricethezav/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz
ENV GITLEAKS_BIN=/usr/bin/gitleaks
ENV OPENSSL_CONF=/app/app/openssl.cnf

WORKDIR /app
RUN echo $GITLEAKS_URL
RUN apt-get update && \
    apt install -y --no-install-recommends ssh-client curl git && \
    apt-get -y --only-upgrade install zlib1g libsqlite3-0 libexpat1 libc-bin libc6 && \
    curl -L -s -o /tmp/gitleaks.tar.gz $GITLEAKS_URL && \
    tar -xvf /tmp/gitleaks.tar.gz -C /tmp/ && \
    cp /tmp/gitleaks $GITLEAKS_BIN && \
    chmod +x $GITLEAKS_BIN && \
    $GITLEAKS_BIN version && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

COPY app/pyproject.toml pyproject.toml
ENV POETRY_HOME=/opt/poetry
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN echo "StrictHostKeyChecking no" >> /etc/ssh_config

RUN curl -sSL https://install.python-poetry.org/ | python - && /opt/poetry/bin/poetry config virtualenvs.create false &&  /opt/poetry/bin/poetry install --no-interaction --no-ansi -vvv


COPY app app
COPY common common
RUN useradd -ms /bin/bash celery

USER celery
CMD ["celery", "-A", "app.celery", "worker", "--concurrency=1"]

FROM python:3.8-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt

CMD ["/usr/local/bin/python", "/app/main.py"]

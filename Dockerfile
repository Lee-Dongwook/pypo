# Step 1.
ARG TORCH_EXTRA=cpu
ARG RUNTIME_SRC=source

FROM python:3.13-slim-bookworm AS main

WORKDIR /app

RUN apt-get update

# Step 2.

FROM main AS builder

ARG TORCH_EXTRA

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \ 
    gcc \ 
    g++ \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/list/*

# WIP

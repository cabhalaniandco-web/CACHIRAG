FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1

# Stable system tooling. The official python image already provides python,
# pip, and venv; we only add git/curl (required for custom images) plus sudo.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        curl \
        ca-certificates \
        sudo \
    && rm -rf /var/lib/apt/lists/*

# Non-root user matching the Cloud Agent convention.
RUN useradd --create-home --shell /bin/bash ubuntu \
    && echo "ubuntu ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ubuntu \
    && chmod 0440 /etc/sudoers.d/ubuntu

USER ubuntu
WORKDIR /home/ubuntu

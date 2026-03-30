# ============================================================
# Dockerfile for GenePattern Module: MultiQC
# Tool:      MultiQC >= 1.14
# Wrapper:   multiqc_wrapper.py  (Python 3)
# Base:      python:3.11-slim
#
# MultiQC aggregates QC reports from many bioinformatics tools
# (FastQC, STAR, Salmon, Picard, Samtools, etc.) into a single
# interactive HTML report.
# ============================================================

FROM python:3.11-slim

# ---------- Metadata ----------
LABEL maintainer="GenePattern Team"
LABEL module.name="MultiQC"
LABEL module.version="1.14"
LABEL module.language="python"
LABEL description="GenePattern wrapper for MultiQC — aggregate bioinformatics QC reports"

# ---------- Working directory ----------
WORKDIR /module

# ---------- System dependencies ----------
# procps  : provides 'ps', useful for debugging inside the container
# ca-certificates : TLS certificate bundle (used by pip/requests)
# curl / wget     : optional, handy for connectivity checks at runtime
# git             : needed by some MultiQC sub-modules that inspect git metadata
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        wget \
        git \
        procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ---------- Python: MultiQC and its runtime dependencies ----------
# multiqc pulls in numpy, matplotlib, Jinja2, click, PyYAML, etc.
# Pin to a stable release that satisfies the ">= 1.14" requirement.
RUN pip install --no-cache-dir \
        "multiqc==1.25.2"

# ---------- Copy wrapper ----------
COPY multiqc_wrapper.py /module/multiqc_wrapper.py
RUN chmod +x /module/multiqc_wrapper.py

# ---------- Environment ----------
ENV MODULE_NAME=MultiQC
ENV MODULE_VERSION=1.14
# Ensure the wrapper is importable as a script from any working directory
ENV PYTHONPATH=/module

# ---------- Default shell (GenePattern overrides CMD at runtime) ----------
CMD ["/bin/bash"]

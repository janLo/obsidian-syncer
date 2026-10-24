FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    python3 \
    python3-venv \
    curl \
    nextcloud-desktop-cmd \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 22.x (Required for obsidian-headless)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Fail the build on Node < 22.23.4 (CVE-2026-111497, bundled Brotli decoder)
RUN node -e 'const [a,b,c]=process.versions.node.split(".").map(Number); process.exit(a>22||(a===22&&(b>23||(b===23&&c>=4)))?0:1)'

# Install uv for python dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Install official obsidian-headless client
RUN npm install -g obsidian-headless

WORKDIR /app

# Copy the project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Create a virtual environment and install the application
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN uv pip install .

# Healthcheck: verify the sync loop has run within the last 10 minutes
HEALTHCHECK --interval=5m --timeout=5s --retries=3 \
  CMD python3 -c "import os,time,sys; f='/tmp/last_sync'; sys.exit(0 if os.path.exists(f) and time.time()-float(open(f).read())<600 else 1)"

# The configuration file is expected to be mounted at /config.yaml
CMD ["obsidian-syncer", "--config", "/config.yaml"]

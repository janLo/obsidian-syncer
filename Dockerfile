FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
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

# The configuration file is expected to be mounted at /config.yaml
CMD ["obsidian-syncer", "--config", "/config.yaml"]

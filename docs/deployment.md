# Deployment

Choose your preferred method to run the sync server:

=== "Docker Compose"

    For a more persistent setup, use Docker Compose. Create a `docker-compose.yml`:

    ```yaml title="docker-compose.yml"
    services:
      obsidian-syncer:
        image: ghcr.io/janlo/obsidian-syncer:latest
        container_name: obsidian-syncer
        restart: unless-stopped
        volumes:
          - ./config.yaml:/config.yaml:ro
          - ./vaults:/vaults
          - ./ob-config:/root/.config
        environment:
          - NC_USER=${NC_USER}
          - NC_PASSWORD=${NC_PASSWORD}
          - KEEP_USER=${KEEP_USER}
          - KEEP_PASSWORD=${KEEP_PASSWORD}
    ```

    Run it in the background:
    ```bash
    docker compose up -d
    ```

=== "Docker CLI"

    Run the container using a bind mount for the configuration, vaults, and obsidian configuration directory:

    ```bash
    docker run -d \
      --name obsidian-syncer \
      -v $(pwd)/config.yaml:/config.yaml \
      -v $(pwd)/vaults:/vaults \
      -v $(pwd)/ob-config:/root/.config \
      -e NC_USER=... \
      -e NC_PASSWORD=... \
      -e KEEP_USER=... \
      -e KEEP_PASSWORD=... \
      ghcr.io/janlo/obsidian-syncer:latest
    ```

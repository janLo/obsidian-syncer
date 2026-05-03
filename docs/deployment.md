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

## Understanding the Volumes

It might seem disconnected at first glance to have a single `config.yaml` file alongside mounted directories. This separation is a common Docker pattern that cleanly divides **instructions** from **data** and **state**:

### 1. `config.yaml` (The Instructions)
This file tells the daemon *what* to do (e.g., which sync sets to run, which tags to look for, and remote URLs). It is mounted as a read-only (`:ro`) file:
```yaml
- ./config.yaml:/config.yaml:ro
```
If you want to change your sync logic, you simply edit this file on your host machine.

### 2. `./vaults` (Your Data Workspace)
This is where your actual Markdown `.md` files live. The `config.yaml` references this directory (e.g., `local_dir: "/vaults/my_vault"`). 
```yaml
- ./vaults:/vaults
```
The container needs read and write access to pull and push files here. Mounting it ensures your notes are safely stored on your host machine and aren't lost when the container is recreated.

### 3. `./ob-config` (The Memory & Internal State)
This directory is essential for **authentication and caching**. 
```yaml
- ./ob-config:/root/.config
```
Tools like the `ob` CLI and `nextcloudcmd` store their session tokens and sync caches in the user's home directory. Without this mount, the container would have "amnesia" upon restarting, and you would lose your Obsidian Sync login session. Mounting it ensures your authentication state persists.

> [!NOTE]
> **In summary:** The container boots up, reads your **Instructions** (`config.yaml`), uses its **Memory** (`/root/.config`) to remember you're already logged in, and manages your notes in the **Workspace** (`/vaults`).

## Health Monitoring

The Docker image includes a built-in `HEALTHCHECK`. After each successful sync cycle, the daemon writes a timestamp to an internal file. Docker verifies every 5 minutes that this timestamp is less than 10 minutes old.

You can check the container's health status at any time:

```bash
docker inspect --format='{{.State.Health.Status}}' obsidian-syncer
```

Or see it in the `docker compose ps` output:

```bash
docker compose ps
```

| Status | Meaning |
|---|---|
| `healthy` | The sync loop completed within the last 10 minutes. |
| `unhealthy` | The sync loop has not completed recently — check logs. |
| `starting` | The container just started and hasn't completed its first cycle yet. |

!!! tip "Auto-Restart on Unhealthy"
    Docker Compose does not natively restart on `unhealthy` status, but you can add the [`autoheal`](https://github.com/willfarrell/docker-autoheal) container alongside your stack, or use Docker Swarm which supports `restart_policy` with health checks.

## Troubleshooting

If you encounter issues during synchronization, you can enable more detailed logging by setting the `LOG_LEVEL` environment variable to `DEBUG`. 

In your `docker-compose.yml`, add it to the `environment` section:

```yaml
    environment:
      - LOG_LEVEL=DEBUG
      # ... other environment variables ...
```

Or pass it via the Docker CLI:

```bash
docker run -d \
  # ... other flags ...
  -e LOG_LEVEL=DEBUG \
  ghcr.io/janlo/obsidian-syncer:latest
```


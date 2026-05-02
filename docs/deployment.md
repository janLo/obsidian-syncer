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

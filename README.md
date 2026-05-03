# Obsidian Sync Server

A headless sync hub running as a Docker container that integrates:
- Obsidian Sync (official `obsidian-headless` client)
- Nextcloud Sync (`nextcloudcmd` client)
- Google Keep (pulling notes via `gkeepapi`)

## Concept

The server runs in daemon mode, syncing multiple "sets" periodically.
Obsidian Sync runs continuously in the background, keeping local files up to date.
Periodically (every 5 minutes by default), the server will:
1. Pull Google Keep notes matching your tags and write them as `.md` files.
2. Synchronize the folder with a remote Nextcloud directory.
   *Conflicts:* Obsidian is considered authoritative. Nextcloud conflict files are automatically deleted to maintain Obsidian's state.

## Setup Configuration

Create a `config.yaml` file mapping your sets:

```yaml
sync_sets:
  - name: "my_vault"
    local_dir: "/vaults/my_vault"
    obsidian:
      enabled: true
    nextcloud:
      enabled: true
      url: "https://nextcloud.example.com"
      user: "${NC_USER}"
      password: "${NC_PASSWORD}"
      remote_folder: "/Obsidian/my_vault"
    keep:
      enabled: true
      username: "${KEEP_USER}"
      password: "${KEEP_PASSWORD}" # Use a Master Token (starts with aas_et/...)
      tags: ["Gemini"]
      target_folder: "/vaults/my_vault/KeepNotes"
```

## Authentication Guidelines

### Obsidian Headless
The `obsidian-headless` tool requires an active Obsidian Sync subscription.
To authenticate, you should run the container interactively once:

1. Open a terminal in the container: `docker exec -it obsidian-syncer bash`
2. Run `ob login` and follow the prompts.
3. Link the vault with `ob sync-setup --vault "YourRemoteVaultName" --path /vaults/my_vault`.
4. Restart the container so the Python daemon picks up the new sync process.

### Google Keep
For reliable syncing, standard passwords and App Passwords are no longer supported for continuous syncing, as Google's security blocks frequent login requests. You **MUST** use a **Master Token**.

To generate a Master Token:
1. Ensure you have 2FA enabled on your Google account and generate an **App Password**.
2. Run the included helper script:
   ```bash
   uv run scripts/get_keep_token.py
   ```
3. Use the generated Master Token (starts with `aas_et/`) as your `KEEP_PASSWORD`.

### Nextcloud
Pass your Nextcloud credentials via environment variables (`NC_USER` and `NC_PASSWORD`). The configuration file will dynamically expand these variables to prevent hardcoding secrets.

## Running with Docker

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

## Running with Docker Compose

For a more persistent setup, you can use Docker Compose. An example `docker-compose.yml` is included in the repository:

```yaml
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

Run the container in the background using:

```bash
docker compose up -d
```

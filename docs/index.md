# Obsidian Sync Server

A headless sync hub running as a Docker container that integrates:

- 💎 **Obsidian Sync** (official `obsidian-headless` client)
- ☁️ **Nextcloud Sync** (`nextcloudcmd` client)
- 📝 **Google Keep** (pulling notes via `gkeepapi`)

## Concept

The server runs in daemon mode, syncing multiple "sets" periodically. Obsidian Sync runs continuously in the background, keeping local files up to date.

Periodically (every 5 minutes by default), the server will:

1. Pull Google Keep notes matching your tags and write them as `.md` files.
2. Synchronize the folder with a remote Nextcloud directory.

!!! info "Conflict Resolution"
    Obsidian is considered authoritative. Nextcloud conflict files are automatically deleted to maintain Obsidian's state.


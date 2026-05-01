# Setup Configuration

Create a `config.yaml` file mapping your sets:

```yaml title="config.yaml"
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
      password: "${KEEP_PASSWORD}" # Use an App Password or Master Token
      tags: ["Gemini"]
      target_folder: "/vaults/my_vault/KeepNotes"
```

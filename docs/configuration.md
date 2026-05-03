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
      tags: ["Obsidian"] # Note must have this tag (or have it extracted via inline_tags_label)
      inline_tags_label: "Gemini" # Extract #tags from text for notes with this Keep label
      ignore_tags: ["synced"] # Notes with this tag will be skipped
      mark_synced_tag: "synced" # Auto-add this tag to a note after downloading it
      target_folder: "/vaults/my_vault/KeepNotes"
```

### Google Keep Syncing Options

- **`tags`**: A list of tags. The syncer will only pull notes from Google Keep that contain ALL of these tags.
- **`inline_tags_label`**: (Optional) A specific Keep label (e.g., `"Gemini"`). If a note has this label in Keep, the syncer will check the note's content for hashtags (e.g., `#Obsidian #Idea`) or a line starting with `Labels:` (e.g., `Labels: tag1, tag2`). These extracted tags are combined with the note's Keep labels and then checked against `tags` and `ignore_tags`. This is especially useful for notes created by external apps (like Gemini or Google Assistant) that cannot natively assign multiple Keep labels. Extracted tags are automatically written back to Google Keep as actual labels on the note, and are also added to the generated Obsidian frontmatter.
- **`ignore_tags`**: (Optional) A list of tags. The syncer will skip any note that has ANY of these tags.
- **`mark_synced_tag`**: (Optional) A single tag. The syncer will automatically add this tag to a note in Google Keep after it has successfully downloaded it. This is typically used in combination with `ignore_tags` to prevent a note from being downloaded again in the future.

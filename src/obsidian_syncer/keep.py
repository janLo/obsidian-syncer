import os
import logging
import gkeepapi
from .config import KeepConfig

logger = logging.getLogger(__name__)

def sync_keep(config: KeepConfig):
    if not config.enabled:
        return
    
    logger.info("Starting Google Keep sync...")
    keep = gkeepapi.Keep()
    try:
        # Check if the user is mistakenly using an App Password instead of a Master Token
        if not config.password.startswith("aas_et/"):
            logger.warning("Your KEEP_PASSWORD does not look like a Master Token. "
                           "If authentication fails, please generate a Master Token. "
                           "Using 'Keep.login' is deprecated and often blocked by Google.")

        keep.authenticate(config.username, config.password)
    except gkeepapi.exception.LoginException as e:
        logger.error(f"Keep Login Exception: {e}")
        if "BadAuthentication" in str(e):
            logger.error("Authentication failed. Please ensure you are using a Master Token "
                         "instead of a standard Google password or App Password. "
                         "You can generate one using the 'scripts/get_keep_token.py' utility.")
        return

    os.makedirs(config.target_folder, exist_ok=True)

    labels = []
    for tag_name in config.tags:
        label = keep.findLabel(tag_name)
        if label:
            labels.append(label)
        else:
            logger.warning(f"Label '{tag_name}' not found in Google Keep.")

    if not labels:
        logger.warning("No labels found to sync.")
        return

    required_label_ids = {label.id for label in labels}

    ignore_labels = []
    for tag_name in config.ignore_tags:
        label = keep.findLabel(tag_name)
        if label:
            ignore_labels.append(label)
        else:
            logger.warning(f"Ignore label '{tag_name}' not found in Google Keep.")

    ignore_label_ids = {label.id for label in ignore_labels}

    # Pass labels to find as an initial filter, then strictly check them all
    notes = keep.find(labels=labels)
    notes_modified = False

    synced_label = None
    if getattr(config, 'mark_synced_tag', None):
        synced_label = keep.findLabel(config.mark_synced_tag)
        if not synced_label:
            logger.info(f"Label '{config.mark_synced_tag}' not found in Keep. Creating it...")
            synced_label = keep.createLabel(config.mark_synced_tag)

    for note in notes:
        # 1. Skip archived or trashed notes
        if note.archived or note.trashed:
            continue
            
        # 2. Strict tag matching (AND condition)
        note_label_ids = {label.id for label in note.labels.all()}
        if not required_label_ids.issubset(note_label_ids):
            continue

        # 3. Check for ignored tags
        if not ignore_label_ids.isdisjoint(note_label_ids):
            logger.info(f"Skipping Keep note '{note.title or 'Untitled'}' due to ignore_tags match.")
            continue

        # Create a safe filename
        title = note.title or "Untitled"
        safe_title = "".join([c for c in title if c.isalnum() or c in ' -_']).strip()
        if not safe_title:
            safe_title = f"Note_{note.id}"
            
        filename = f"{safe_title}.md"
        filepath = os.path.join(config.target_folder, filename)

        # 4. Add frontmatter with metadata
        created_str = note.timestamps.created.isoformat()
        note_tags = [label.name for label in note.labels.all()]
        
        frontmatter = "---\n"
        frontmatter += f"created: {created_str}\n"
        if note_tags:
            frontmatter += "tags:\n"
            for tag in note_tags:
                # remove spaces from tags to be safe, or just keep them? Obsidian supports spaces in frontmatter tags
                frontmatter += f"  - {tag}\n"
        frontmatter += "---\n"

        content = f"{frontmatter}\n# {title}\n\n{note.text}\n"

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Saved Keep note: {filename}")
            
            if synced_label:
                note.labels.add(synced_label)
                notes_modified = True
                logger.info(f"Added tag '{config.mark_synced_tag}' to Keep note '{title}'.")
        except Exception as e:
            logger.error(f"Failed to save Keep note {filename}: {e}")

    if notes_modified:
        logger.info("Pushing tag updates back to Google Keep...")
        try:
            keep.sync()
            logger.info("Successfully pushed updates to Google Keep.")
        except Exception as e:
            logger.error(f"Failed to push updates to Google Keep: {e}")

    logger.info("Google Keep sync completed.")

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

    required_tag_names = set(config.tags)
    ignore_tag_names = set(config.ignore_tags)

    if not required_tag_names:
        logger.warning("No tags specified in config to sync.")
        return

    for tag_name in config.ignore_tags:
        if not keep.findLabel(tag_name):
            logger.warning(f"Ignore label '{tag_name}' not found in Google Keep.")

    for tag_name in config.tags:
        if not keep.findLabel(tag_name):
            logger.warning(f"Label '{tag_name}' not found in Google Keep.")

    notes = keep.all()
    notes_modified = False

    synced_label = None
    if config.mark_synced_tag:
        synced_label = keep.findLabel(config.mark_synced_tag)
        if not synced_label:
            logger.info(f"Label '{config.mark_synced_tag}' not found in Keep. Creating it...")
            synced_label = keep.createLabel(config.mark_synced_tag)

    for note in notes:
        # 1. Skip archived or trashed notes
        if note.archived or note.trashed:
            continue
            
        note_tags_names = {label.name for label in note.labels.all()}

        # Check if the note has a Gemini WebLink annotation
        has_gemini_link = False
        if hasattr(note, 'annotations'):
            has_gemini_link = any(
                isinstance(item, gkeepapi.node.WebLink) and getattr(item, 'url', '').startswith("https://gemini.google.com")
                for ann in note.annotations.all()
                for item in ann.all()
            )

        # Parse inline tags if the note has the inline_tags_label or a Gemini link
        if (config.inline_tags_label and config.inline_tags_label in note_tags_names) or has_gemini_link:
            note_text = getattr(note, 'text', '')
            lines = note_text.strip().splitlines()
            if lines:
                import re
                # Examine the last few lines for tags and labels
                for line in lines[-5:]:
                    line_stripped = line.strip()
                    if not line_stripped:
                        continue
                    
                    if line_stripped.lower().startswith("labels:"):
                        labels_str = line_stripped[7:].strip()
                        # Split by comma or space
                        extracted_labels = [l for l in re.split(r'[,\s]+', labels_str) if l]
                        note_tags_names.update(extracted_labels)
                    
                    hashtags = re.findall(r'#([A-Za-z0-9_/-]+)', line_stripped)
                    if hashtags:
                        note_tags_names.update(hashtags)

        # 2. Strict tag matching (AND condition)
        if not required_tag_names.issubset(note_tags_names):
            continue

        # 3. Check for ignored tags
        if not ignore_tag_names.isdisjoint(note_tags_names):
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
        frontmatter = "---\n"
        frontmatter += f"created: {created_str}\n"
        if note_tags_names:
            frontmatter += "tags:\n"
            for tag in sorted(note_tags_names):
                # remove spaces from tags to be safe, or just keep them? Obsidian supports spaces in frontmatter tags
                frontmatter += f"  - {tag}\n"
        frontmatter += "---\n"

        content = f"{frontmatter}\n# {title}\n\n{getattr(note, 'text', '')}\n"

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

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

    notes = keep.find(labels=labels)
    for note in notes:
        # Create a safe filename
        title = note.title or "Untitled"
        safe_title = "".join([c for c in title if c.isalnum() or c in ' -_']).strip()
        if not safe_title:
            safe_title = f"Note_{note.id}"
            
        filename = f"{safe_title}.md"
        filepath = os.path.join(config.target_folder, filename)

        content = f"# {title}\n\n{note.text}\n"

        try:
            # We are doing a simple pull-only.
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Saved Keep note: {filename}")
        except Exception as e:
            logger.error(f"Failed to save Keep note {filename}: {e}")

    logger.info("Google Keep sync completed.")

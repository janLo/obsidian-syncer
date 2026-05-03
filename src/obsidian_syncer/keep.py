import os
import re
import logging
from typing import Set, List
import gkeepapi
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from .config import KeepConfig

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
    before_sleep=lambda rs: logger.warning(
        f"Retrying Keep auth (attempt {rs.attempt_number})..."
    ),
)
def authenticate_keep(keep: gkeepapi.Keep, config: KeepConfig) -> bool:
    """Authenticates with Google Keep and handles deprecated auth warnings."""
    try:
        # Check if the user is mistakenly using an App Password instead of a Master Token
        if not config.password.startswith("aas_et/"):
            logger.warning(
                "Your KEEP_PASSWORD does not look like a Master Token. "
                "If authentication fails, please generate a Master Token. "
                "Using 'Keep.login' is deprecated and often blocked by Google."
            )

        keep.authenticate(config.username, config.password)
        return True
    except gkeepapi.exception.LoginException as e:
        logger.error(f"Keep Login Exception: {e}")
        if "BadAuthentication" in str(e):
            logger.error(
                "Authentication failed. Please ensure you are using a Master Token "
                "instead of a standard Google password or App Password. "
                "You can generate one using the 'scripts/get_keep_token.py' utility."
            )
        return False


def get_or_create_label(keep: gkeepapi.Keep, label_name: str) -> gkeepapi.node.Label:
    """Finds a label by name (case-insensitive) or creates it if it doesn't exist."""
    label = keep.findLabel(label_name)
    if label:
        return label

    # Fallback to manual case-insensitive search
    for existing_label in keep.labels():
        if existing_label.name.lower() == label_name.lower():
            return existing_label

    logger.info(f"Label '{label_name}' not found in Keep. Creating it...")
    return keep.createLabel(label_name)


def has_gemini_link(note: gkeepapi.node.Note) -> bool:
    """Checks if the note has a Gemini WebLink annotation."""
    if not hasattr(note, "annotations") or note.annotations is None:
        return False

    def _iter_annotations(annotations_obj):
        for ann in annotations_obj.all():
            yield ann
            if hasattr(ann, "all"):
                yield from ann.all()

    return any(
        isinstance(ann, gkeepapi.node.WebLink)
        and getattr(ann, "url", "").startswith("https://gemini.google.com")
        for ann in _iter_annotations(note.annotations)
    )


def extract_inline_tags(note_text: str) -> List[str]:
    """Extracts tags from the last few lines of the note text."""
    extracted_tags = []
    lines = note_text.strip().splitlines()
    if not lines:
        return extracted_tags

    # Examine the last few lines for tags and labels
    for line in lines[-5:]:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Check for 'Labels:' prefix
        if line_stripped.lower().startswith("labels:"):
            labels_str = line_stripped[7:].strip()
            # Split by comma or space
            extracted_labels = [lbl for lbl in re.split(r"[,\s]+", labels_str) if lbl]
            extracted_tags.extend(extracted_labels)

        # Check for hashtags
        hashtags = re.findall(r"#([A-Za-z0-9_/-]+)", line_stripped)
        if hashtags:
            extracted_tags.extend(hashtags)

    return extracted_tags


def should_sync_note(
    note_tags_names: Set[str], required_tag_names: Set[str], ignore_tag_names: Set[str]
) -> bool:
    """Checks if the note has required tags and no ignored tags."""
    if not required_tag_names.issubset(note_tags_names):
        return False

    if not ignore_tag_names.isdisjoint(note_tags_names):
        return False

    return True


def format_note_content(note: gkeepapi.node.Note, note_tags_names: Set[str]) -> str:
    """Formats the note content as a Markdown string with frontmatter."""
    title = note.title or "Untitled"
    created_str = note.timestamps.created.isoformat()

    frontmatter = "---\n"
    frontmatter += f"created: {created_str}\n"
    if note_tags_names:
        frontmatter += "tags:\n"
        for tag in sorted(note_tags_names):
            frontmatter += f"  - {tag}\n"
    frontmatter += "---\n"

    content = f"{frontmatter}\n# {title}\n\n{getattr(note, 'text', '')}\n"
    return content


def save_note_to_disk(
    note: gkeepapi.node.Note, content: str, target_folder: str
) -> str:
    """Saves the Markdown content to a file. Returns the filename."""
    title = note.title or "Untitled"
    safe_title = "".join([c for c in title if c.isalnum() or c in " -_"]).strip()
    if not safe_title:
        safe_title = f"Note_{note.id}"

    filename = f"{safe_title}.md"
    filepath = os.path.join(target_folder, filename)

    # Atomic write: write to a temp file, then replace
    tmp_filepath = filepath + ".tmp"
    with open(tmp_filepath, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp_filepath, filepath)

    return filename


def check_config_labels(keep: gkeepapi.Keep, config: KeepConfig) -> None:
    """Checks if the configured labels exist in Keep and logs warnings if not."""
    keep_label_names = {label.name.lower() for label in keep.labels()}

    for tag_name in config.ignore_tags:
        if tag_name.lower() not in keep_label_names:
            logger.warning(f"Ignore label '{tag_name}' not found in Google Keep.")

    for tag_name in config.tags:
        if tag_name.lower() not in keep_label_names:
            logger.warning(f"Label '{tag_name}' not found in Google Keep.")


def sync_keep(config: KeepConfig):
    """Main function to synchronize Google Keep notes."""
    if not config.enabled:
        return

    logger.info("Starting Google Keep sync...")
    keep = gkeepapi.Keep()

    if not authenticate_keep(keep, config):
        return

    os.makedirs(config.target_folder, exist_ok=True)

    required_tag_names = {t.lower() for t in config.tags}
    ignore_tag_names = {t.lower() for t in config.ignore_tags}

    if not required_tag_names:
        logger.warning("No tags specified in config to sync.")
        return

    check_config_labels(keep, config)

    notes = keep.all()
    notes_modified = False

    synced_label = None
    if config.mark_synced_tag:
        synced_label = get_or_create_label(keep, config.mark_synced_tag)

    for note in notes:
        # 1. Skip archived or trashed notes
        if note.archived or note.trashed:
            continue

        original_note_tags_names = {label.name.lower() for label in note.labels.all()}
        note_tags_names = set(original_note_tags_names)
        extracted_tags_original_case = []

        # 2. Check for inline tags
        has_gemini = has_gemini_link(note)
        has_inline_tags_label = (
            config.inline_tags_label
            and config.inline_tags_label.lower() in note_tags_names
        )

        if has_inline_tags_label or has_gemini:
            note_text = getattr(note, "text", "")
            extracted_tags_original_case = extract_inline_tags(note_text)
            note_tags_names.update([t.lower() for t in extracted_tags_original_case])

        # 3. Add extracted tags back to Keep
        if extracted_tags_original_case:
            for tag_original in extracted_tags_original_case:
                tag_lower = tag_original.lower()
                if tag_lower not in original_note_tags_names:
                    new_label = get_or_create_label(keep, tag_original)
                    note.labels.add(new_label)
                    notes_modified = True
                    original_note_tags_names.add(tag_lower)
                    logger.info(
                        f"Added extracted tag '{tag_original}' to Keep note '{note.title or 'Untitled'}'."
                    )

        # 4. Strict tag matching & ignored tags
        if not should_sync_note(note_tags_names, required_tag_names, ignore_tag_names):
            if not ignore_tag_names.isdisjoint(
                note_tags_names
            ) and required_tag_names.issubset(note_tags_names):
                logger.info(
                    f"Skipping Keep note '{note.title or 'Untitled'}' due to ignore_tags match."
                )
            continue

        # 5. Format and Save Note
        content = format_note_content(note, note_tags_names)
        try:
            filename = save_note_to_disk(note, content, config.target_folder)
            logger.info(f"Saved Keep note: {filename}")

            if synced_label:
                note.labels.add(synced_label)
                notes_modified = True
                logger.info(
                    f"Added tag '{config.mark_synced_tag}' to Keep note '{note.title or 'Untitled'}'."
                )
        except Exception as e:
            logger.error(f"Failed to save Keep note '{note.title or 'Untitled'}': {e}")

    # 6. Sync changes back to Keep
    if notes_modified:
        logger.info("Pushing tag updates back to Google Keep...")
        try:
            _push_keep_changes(keep)
            logger.info("Successfully pushed updates to Google Keep.")
        except Exception as e:
            logger.error(f"Failed to push updates to Google Keep: {e}")

    logger.info("Google Keep sync completed.")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
    before_sleep=lambda rs: logger.warning(
        f"Retrying Keep sync push (attempt {rs.attempt_number})..."
    ),
)
def _push_keep_changes(keep: gkeepapi.Keep):
    """Pushes local label changes back to Google Keep with retry."""
    keep.sync()

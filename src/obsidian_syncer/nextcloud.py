import subprocess
import logging
import os
import glob
from .config import SyncSet

logger = logging.getLogger(__name__)

def sync_nextcloud(sync_set: SyncSet):
    config = sync_set.nextcloud
    if not config or not config.enabled:
        return

    logger.info("Starting Nextcloud sync...")
    
    # nextcloudcmd [OPTIONS] <source_dir> <server_url>
    cmd = [
        "nextcloudcmd",
        "--user", config.user,
        "--password", config.password,
        "--path", config.remote_folder,
        "--non-interactive",
        sync_set.local_dir,
        config.url
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Nextcloud sync failed with return code {result.returncode}")
            logger.debug(f"Nextcloud stderr: {result.stderr}")
        else:
            logger.info("Nextcloud sync completed successfully.")
            
        # Handle conflicts: Obsidian is authoritative, delete Nextcloud conflict files
        search_pattern = os.path.join(sync_set.local_dir, "**", "*_conflict-*")
        conflict_files = glob.glob(search_pattern, recursive=True)
        for conflict_file in conflict_files:
            try:
                os.remove(conflict_file)
                logger.info(f"Deleted conflict file to maintain Obsidian authority: {conflict_file}")
            except OSError as e:
                logger.error(f"Failed to delete conflict file {conflict_file}: {e}")

    except FileNotFoundError:
        logger.error("nextcloudcmd not found. Ensure it is installed in the system.")
    except Exception as e:
        logger.error(f"Nextcloud sync encountered an error: {e}")

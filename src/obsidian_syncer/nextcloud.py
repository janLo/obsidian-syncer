import subprocess
import logging
import os
import glob
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from .config import SyncSet

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=5, max=60),
    retry=retry_if_exception_type((OSError, subprocess.SubprocessError)),
    before_sleep=lambda rs: logger.warning(
        f"Retrying nextcloudcmd (attempt {rs.attempt_number})..."
    ),
)
def _run_nextcloudcmd(cmd, env):
    """Runs nextcloudcmd with retry on process-level failures.

    Only retries on OS-level errors (e.g. process couldn't start).
    Non-zero exit codes from nextcloudcmd are NOT retried because they
    typically indicate partial sync issues (conflicts, permission errors)
    that won't resolve by re-running immediately.
    """
    return subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env
    )


def sync_nextcloud(sync_set: SyncSet):
    config = sync_set.nextcloud
    if not config or not config.enabled:
        return

    logger.info("Starting Nextcloud sync...")

    # Pass credentials via environment variables instead of CLI flags
    # to avoid exposing passwords in the process list (ps aux).
    env = os.environ.copy()
    env["NC_USER"] = config.user
    env["NC_PASSWORD"] = config.password

    # nextcloudcmd [OPTIONS] <source_dir> <server_url>
    cmd = [
        "nextcloudcmd",
        "--path",
        config.remote_folder,
        "--non-interactive",
        sync_set.local_dir,
        config.url,
    ]

    try:
        result = _run_nextcloudcmd(cmd, env)

        if result.returncode != 0:
            logger.error(f"Nextcloud sync failed with return code {result.returncode}")
            logger.debug(f"Nextcloud stderr: {result.stderr}")
        else:
            logger.info("Nextcloud sync completed successfully.")

        # Handle conflicts regardless of exit code — Obsidian is authoritative
        _cleanup_conflict_files(sync_set.local_dir)

    except FileNotFoundError:
        logger.error("nextcloudcmd not found. Ensure it is installed in the system.")
    except Exception as e:
        logger.error(f"Nextcloud sync encountered an error: {e}")
        # Still attempt conflict cleanup even after errors
        _cleanup_conflict_files(sync_set.local_dir)


def _cleanup_conflict_files(local_dir: str):
    """Deletes Nextcloud conflict files, logging their content first."""
    search_pattern = os.path.join(local_dir, "**", "*_conflict-*")
    conflict_files = glob.glob(search_pattern, recursive=True)
    for conflict_file in conflict_files:
        try:
            # Log a preview of the conflict content before discarding
            try:
                with open(conflict_file, "r", encoding="utf-8", errors="replace") as cf:
                    preview = cf.read(500)
                logger.warning(
                    f"Discarding conflict file {conflict_file}. Preview:\n{preview}"
                )
            except Exception:
                logger.warning(
                    f"Discarding conflict file {conflict_file} "
                    f"(could not read preview)."
                )
            os.remove(conflict_file)
            logger.info(
                f"Deleted conflict file to maintain Obsidian authority: {conflict_file}"
            )
        except OSError as e:
            logger.error(f"Failed to delete conflict file {conflict_file}: {e}")

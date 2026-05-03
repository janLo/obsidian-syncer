import time
import pathlib
import argparse
import logging
import signal
import sys
import traceback

from .config import load_config
from .obsidian import ObsidianProcessManager
from .nextcloud import sync_nextcloud
from .keep import sync_keep

import os

logger = logging.getLogger(__name__)

# Default sync interval: 5 minutes
DEFAULT_SYNC_INTERVAL = 300

HEALTHCHECK_FILE = pathlib.Path("/tmp/last_sync")


def setup_logging():
    """Configures root logging based on the LOG_LEVEL environment variable."""
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logging.basicConfig(
        level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )


def handle_exit(signum, frame, manager: ObsidianProcessManager):
    """Gracefully shuts down background processes on signal."""
    logger.info("Shutdown signal received. Stopping services...")
    manager.stop_all()
    sys.exit(0)


def run_sync_loop(app_config, manager: ObsidianProcessManager, interval: int):
    """Main sync loop. Separated from main() for testability."""
    # Initial start of background services
    for sync_set in app_config.sync_sets:
        manager.start_obsidian(sync_set)

    logger.info("Entering main sync loop...")

    while True:
        for sync_set in app_config.sync_sets:
            logger.info(f"--- Processing Sync Set: {sync_set.name} ---")

            # Ensure Obsidian is still running
            manager.start_obsidian(sync_set)

            try:
                # 1. Pull from Keep
                if sync_set.keep and sync_set.keep.enabled:
                    sync_keep(sync_set.keep)

                # 2. Sync with Nextcloud
                if sync_set.nextcloud and sync_set.nextcloud.enabled:
                    sync_nextcloud(sync_set)
            except Exception as e:
                logger.error(f"Error processing sync set {sync_set.name}: {e}")
                logger.error(traceback.format_exc())

        # Write healthcheck timestamp after each successful cycle
        try:
            HEALTHCHECK_FILE.write_text(str(time.time()))
        except OSError:
            logger.debug("Failed to write healthcheck file (non-critical).")

        logger.info(f"Sync complete. Sleeping for {interval} seconds...")
        time.sleep(interval)


def main():
    setup_logging()

    parser = argparse.ArgumentParser(description="Obsidian Sync Server")
    parser.add_argument(
        "--config", default="config.yaml", help="Path to the configuration YAML file"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_SYNC_INTERVAL,
        help="Sync interval in seconds (default: 300)",
    )

    args = parser.parse_args()

    try:
        app_config = load_config(args.config)
        logger.info(f"Loaded configuration from {args.config}")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    manager = ObsidianProcessManager()

    # Install signal handlers with the manager instance
    signal.signal(signal.SIGINT, lambda s, f: handle_exit(s, f, manager))
    signal.signal(signal.SIGTERM, lambda s, f: handle_exit(s, f, manager))

    try:
        run_sync_loop(app_config, manager, args.interval)
    except KeyboardInterrupt:
        handle_exit(signal.SIGINT, None, manager)


if __name__ == "__main__":
    main()

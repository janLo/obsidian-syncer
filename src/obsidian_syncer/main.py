import time
import argparse
import logging
import signal
import sys
import traceback

from .config import load_config
from .obsidian import obsidian_manager
from .nextcloud import sync_nextcloud
from .keep import sync_keep

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Default sync interval: 5 minutes
SYNC_INTERVAL = 300

def handle_exit(signum, frame):
    logger.info("Shutdown signal received. Stopping services...")
    obsidian_manager.stop_all()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def main():
    parser = argparse.ArgumentParser(description="Obsidian Sync Server")
    parser.add_argument(
        "--config", 
        default="config.yaml", 
        help="Path to the configuration YAML file"
    )
    parser.add_argument(
        "--interval", 
        type=int, 
        default=SYNC_INTERVAL, 
        help="Sync interval in seconds (default: 300)"
    )
    
    args = parser.parse_args()

    try:
        app_config = load_config(args.config)
        logger.info(f"Loaded configuration from {args.config}")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    # Initial start of background services
    for sync_set in app_config.sync_sets:
        obsidian_manager.start_obsidian(sync_set)

    logger.info("Entering main sync loop...")
    
    while True:
        for sync_set in app_config.sync_sets:
            logger.info(f"--- Processing Sync Set: {sync_set.name} ---")
            
            # Ensure Obsidian is still running
            obsidian_manager.start_obsidian(sync_set)
            
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

        logger.info(f"Sync complete. Sleeping for {args.interval} seconds...")
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            handle_exit(signal.SIGINT, None)

if __name__ == "__main__":
    main()

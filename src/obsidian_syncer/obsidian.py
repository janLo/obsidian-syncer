import subprocess
import logging
import os
from typing import Dict
from .config import SyncSet

logger = logging.getLogger(__name__)

class ObsidianProcessManager:
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}

    def start_obsidian(self, sync_set: SyncSet):
        config = sync_set.obsidian
        if not config or not config.enabled:
            return

        if sync_set.name in self.processes:
            # Check if still alive
            if self.processes[sync_set.name].poll() is None:
                logger.debug(f"Obsidian already running for {sync_set.name}")
                return
            else:
                logger.warning(f"Obsidian process for {sync_set.name} died, restarting.")

        logger.info(f"Starting Obsidian Headless for {sync_set.name} at {sync_set.local_dir}")
        
        # and uses the local directory as the vault.
        cmd = ["ob", "sync", "--continuous", "--path", sync_set.local_dir]

        try:
            # Running as background process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                text=True,
                env=os.environ.copy() # Passes OBSIDIAN_AUTH_TOKEN if set
            )
            self.processes[sync_set.name] = process
            logger.info(f"Started Obsidian Headless process (PID: {process.pid}) for {sync_set.name}")
        except FileNotFoundError:
            logger.error("ob command not found. Please ensure obsidian-headless is installed (npm install -g obsidian-headless).")
        except Exception as e:
            logger.error(f"Failed to start Obsidian Headless: {e}")

    def stop_all(self):
        for name, process in self.processes.items():
            if process.poll() is None:
                logger.info(f"Stopping Obsidian process for {name} (PID: {process.pid})")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing Obsidian process {process.pid}")
                    process.kill()
        self.processes.clear()

obsidian_manager = ObsidianProcessManager()

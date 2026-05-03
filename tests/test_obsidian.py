"""Tests for the ObsidianProcessManager."""

from unittest.mock import patch, MagicMock

from obsidian_syncer.obsidian import ObsidianProcessManager
from obsidian_syncer.config import SyncSet, ObsidianConfig


def _make_sync_set(name="test_vault", enabled=True):
    """Helper to create a SyncSet with Obsidian config."""
    return SyncSet(
        name=name,
        local_dir="/vaults/test",
        obsidian=ObsidianConfig(enabled=enabled),
    )


@patch("obsidian_syncer.obsidian.subprocess.Popen")
def test_start_obsidian_launches_process(mock_popen):
    """start_obsidian launches the ob process with correct args."""
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_process.poll.return_value = None  # process is running
    mock_popen.return_value = mock_process

    manager = ObsidianProcessManager()
    sync_set = _make_sync_set()

    manager.start_obsidian(sync_set)

    mock_popen.assert_called_once()
    cmd = mock_popen.call_args[0][0]
    assert cmd == ["ob", "sync", "--continuous", "--path", "/vaults/test"]
    assert "test_vault" in manager.processes


@patch("obsidian_syncer.obsidian.subprocess.Popen")
def test_start_obsidian_skips_if_running(mock_popen):
    """start_obsidian does not relaunch if the process is still alive."""
    mock_process = MagicMock()
    mock_process.poll.return_value = None  # still running
    mock_popen.return_value = mock_process

    manager = ObsidianProcessManager()
    sync_set = _make_sync_set()

    manager.start_obsidian(sync_set)
    manager.start_obsidian(sync_set)  # second call

    # Popen should only be called once
    assert mock_popen.call_count == 1


@patch("obsidian_syncer.obsidian.subprocess.Popen")
def test_start_obsidian_restarts_crashed_process(mock_popen):
    """start_obsidian restarts a process that has exited."""
    mock_process_1 = MagicMock()
    mock_process_1.pid = 111
    mock_process_1.poll.return_value = None  # running initially
    mock_popen.return_value = mock_process_1

    manager = ObsidianProcessManager()
    sync_set = _make_sync_set()

    manager.start_obsidian(sync_set)
    assert mock_popen.call_count == 1

    # Simulate crash
    mock_process_1.poll.return_value = 1  # process exited

    mock_process_2 = MagicMock()
    mock_process_2.pid = 222
    mock_process_2.poll.return_value = None
    mock_popen.return_value = mock_process_2

    manager.start_obsidian(sync_set)
    assert mock_popen.call_count == 2


def test_start_obsidian_disabled():
    """start_obsidian does nothing when Obsidian is disabled."""
    manager = ObsidianProcessManager()
    sync_set = _make_sync_set(enabled=False)

    manager.start_obsidian(sync_set)
    assert len(manager.processes) == 0


def test_start_obsidian_no_config():
    """start_obsidian does nothing when there's no Obsidian config."""
    manager = ObsidianProcessManager()
    sync_set = SyncSet(name="test", local_dir="/vaults/test")

    manager.start_obsidian(sync_set)
    assert len(manager.processes) == 0


@patch("obsidian_syncer.obsidian.subprocess.Popen")
def test_stop_all_terminates_processes(mock_popen):
    """stop_all terminates all running processes and clears the dict."""
    mock_process = MagicMock()
    mock_process.pid = 999
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process

    manager = ObsidianProcessManager()
    manager.start_obsidian(_make_sync_set("vault1"))

    mock_process2 = MagicMock()
    mock_process2.pid = 888
    mock_process2.poll.return_value = None
    mock_popen.return_value = mock_process2
    manager.start_obsidian(_make_sync_set("vault2"))

    manager.stop_all()

    mock_process.terminate.assert_called_once()
    mock_process2.terminate.assert_called_once()
    assert len(manager.processes) == 0


@patch("obsidian_syncer.obsidian.subprocess.Popen")
def test_stop_all_force_kills_stubborn_process(mock_popen):
    """stop_all force-kills a process that doesn't terminate within timeout."""
    import subprocess

    mock_process = MagicMock()
    mock_process.pid = 999
    mock_process.poll.return_value = None
    mock_process.wait.side_effect = subprocess.TimeoutExpired(cmd="ob", timeout=5)
    mock_popen.return_value = mock_process

    manager = ObsidianProcessManager()
    manager.start_obsidian(_make_sync_set())

    manager.stop_all()

    mock_process.terminate.assert_called_once()
    mock_process.kill.assert_called_once()

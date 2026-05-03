"""Tests for the Nextcloud sync module."""

import os
import tempfile
from unittest.mock import patch, MagicMock

from obsidian_syncer.nextcloud import sync_nextcloud, _cleanup_conflict_files
from obsidian_syncer.config import SyncSet, NextcloudConfig


def _make_sync_set(local_dir="/tmp/vault"):
    """Helper to create a SyncSet with Nextcloud config."""
    return SyncSet(
        name="test_set",
        local_dir=local_dir,
        nextcloud=NextcloudConfig(
            enabled=True,
            url="https://nextcloud.example.com",
            user="testuser",
            password="secret_password",
            remote_folder="/Obsidian/vault",
        ),
    )


@patch("obsidian_syncer.nextcloud._run_nextcloudcmd")
def test_sync_nextcloud_correct_cmd(mock_run):
    """The nextcloudcmd command has the correct structure."""
    mock_run.return_value = MagicMock(returncode=0)

    with tempfile.TemporaryDirectory() as tmpdir:
        sync_set = _make_sync_set(local_dir=tmpdir)
        sync_nextcloud(sync_set)

        args, _ = mock_run.call_args
        cmd = args[0]

        assert cmd[0] == "nextcloudcmd"
        assert "--user" in cmd
        assert "--password" in cmd
        assert "--path" in cmd
        assert "/Obsidian/vault" in cmd
        assert "--non-interactive" in cmd
        assert tmpdir in cmd
        assert "https://nextcloud.example.com" in cmd


@patch("obsidian_syncer.nextcloud._run_nextcloudcmd")
def test_sync_nextcloud_deletes_conflict_files(mock_run):
    """Conflict files are deleted and their content is logged."""
    mock_run.return_value = MagicMock(returncode=0)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a fake conflict file
        conflict_path = os.path.join(tmpdir, "note_conflict-20240101.md")
        with open(conflict_path, "w") as f:
            f.write("Conflicting content here")

        sync_set = _make_sync_set(local_dir=tmpdir)
        sync_nextcloud(sync_set)

        # Conflict file should be deleted
        assert not os.path.exists(conflict_path)


@patch("obsidian_syncer.nextcloud._run_nextcloudcmd")
def test_sync_nextcloud_cleans_conflicts_even_on_nonzero_exit(mock_run):
    """Conflict cleanup runs even when nextcloudcmd returns non-zero."""
    mock_run.return_value = MagicMock(returncode=1, stderr="some error")

    with tempfile.TemporaryDirectory() as tmpdir:
        conflict_path = os.path.join(tmpdir, "note_conflict-20240101.md")
        with open(conflict_path, "w") as f:
            f.write("Conflicting content")

        sync_set = _make_sync_set(local_dir=tmpdir)
        sync_nextcloud(sync_set)

        assert not os.path.exists(conflict_path)


@patch("obsidian_syncer.nextcloud._run_nextcloudcmd")
def test_sync_nextcloud_disabled(mock_run):
    """Sync does nothing when Nextcloud is disabled."""
    sync_set = SyncSet(
        name="test_set",
        local_dir="/tmp/vault",
        nextcloud=NextcloudConfig(
            enabled=False,
            url="https://nextcloud.example.com",
            user="testuser",
            password="secret",
            remote_folder="/Obsidian/vault",
        ),
    )

    sync_nextcloud(sync_set)
    mock_run.assert_not_called()


@patch("obsidian_syncer.nextcloud._run_nextcloudcmd")
def test_sync_nextcloud_no_config(mock_run):
    """Sync does nothing when there's no Nextcloud config."""
    sync_set = SyncSet(name="test_set", local_dir="/tmp/vault")
    sync_nextcloud(sync_set)
    mock_run.assert_not_called()


def test_cleanup_conflict_files():
    """_cleanup_conflict_files deletes conflict files independently."""
    with tempfile.TemporaryDirectory() as tmpdir:
        conflict_path = os.path.join(tmpdir, "doc_conflict-20240101.md")
        normal_path = os.path.join(tmpdir, "normal_note.md")
        with open(conflict_path, "w") as f:
            f.write("conflict")
        with open(normal_path, "w") as f:
            f.write("normal")

        _cleanup_conflict_files(tmpdir)

        assert not os.path.exists(conflict_path)
        assert os.path.exists(normal_path)

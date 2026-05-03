"""Integration tests for the sync_keep orchestration."""

import os
import tempfile
from unittest.mock import MagicMock, patch
from datetime import datetime

import gkeepapi

from obsidian_syncer.keep import sync_keep
from obsidian_syncer.config import KeepConfig


def _make_mock_note(
    title="Test Note",
    text="Hello world",
    note_id="abc123",
    labels=None,
    archived=False,
    trashed=False,
    annotations=None,
):
    """Helper to create a mock gkeepapi Note."""
    note = MagicMock(spec=gkeepapi.node.Note)
    note.title = title
    note.text = text
    note.id = note_id
    note.archived = archived
    note.trashed = trashed
    note.timestamps.created = datetime(2024, 1, 15, 10, 30, 0)

    # Labels mock
    mock_labels = []
    if labels:
        for name in labels:
            lbl = MagicMock()
            lbl.name = name
            mock_labels.append(lbl)
    note.labels.all.return_value = mock_labels

    # Annotations mock
    if annotations is None:
        note.annotations = None
    else:
        note.annotations = annotations

    return note


def _make_config(
    tags=None,
    ignore_tags=None,
    mark_synced_tag=None,
    inline_tags_label=None,
    target_folder="/tmp/test_vault",
):
    """Helper to create a KeepConfig for tests."""
    return KeepConfig(
        enabled=True,
        username="test@example.com",
        password="aas_et/fake_token",
        tags=tags or ["Obsidian"],
        ignore_tags=ignore_tags or [],
        inline_tags_label=inline_tags_label,
        mark_synced_tag=mark_synced_tag,
        target_folder=target_folder,
    )


@patch("obsidian_syncer.keep.gkeepapi.Keep")
def test_sync_keep_saves_matching_note(MockKeep):
    """A note with the required tag is saved to disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _make_config(tags=["Obsidian"], target_folder=tmpdir)

        keep_instance = MockKeep.return_value
        keep_instance.authenticate.return_value = True
        keep_instance.labels.return_value = []
        keep_instance.findLabel.return_value = None

        note = _make_mock_note(title="My Note", text="Content", labels=["Obsidian"])
        keep_instance.all.return_value = [note]

        sync_keep(config)

        # Assert the file was created
        expected_file = os.path.join(tmpdir, "My Note.md")
        assert os.path.exists(expected_file)

        content = open(expected_file).read()
        assert "# My Note" in content
        assert "Content" in content
        assert "obsidian" in content  # tag in frontmatter (lowercased)


@patch("obsidian_syncer.keep.gkeepapi.Keep")
def test_sync_keep_skips_archived_notes(MockKeep):
    """Archived notes are not synced."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _make_config(tags=["Obsidian"], target_folder=tmpdir)

        keep_instance = MockKeep.return_value
        keep_instance.authenticate.return_value = True
        keep_instance.labels.return_value = []
        keep_instance.findLabel.return_value = None

        note = _make_mock_note(title="Archived", labels=["Obsidian"], archived=True)
        keep_instance.all.return_value = [note]

        sync_keep(config)

        assert not os.path.exists(os.path.join(tmpdir, "Archived.md"))


@patch("obsidian_syncer.keep.gkeepapi.Keep")
def test_sync_keep_skips_ignored_tags(MockKeep):
    """Notes with ignore_tags are skipped even if they have required tags."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _make_config(
            tags=["Obsidian"], ignore_tags=["synced"], target_folder=tmpdir
        )

        keep_instance = MockKeep.return_value
        keep_instance.authenticate.return_value = True
        keep_instance.labels.return_value = []
        keep_instance.findLabel.return_value = None

        note = _make_mock_note(title="Already Synced", labels=["Obsidian", "synced"])
        keep_instance.all.return_value = [note]

        sync_keep(config)

        assert not os.path.exists(os.path.join(tmpdir, "Already Synced.md"))


@patch("obsidian_syncer.keep.gkeepapi.Keep")
def test_sync_keep_applies_synced_tag(MockKeep):
    """After saving, the mark_synced_tag is added to the note."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _make_config(
            tags=["Obsidian"], mark_synced_tag="synced", target_folder=tmpdir
        )

        keep_instance = MockKeep.return_value
        keep_instance.authenticate.return_value = True
        keep_instance.labels.return_value = []

        synced_label = MagicMock()
        synced_label.name = "synced"
        keep_instance.findLabel.return_value = synced_label

        note = _make_mock_note(title="Tag Me", labels=["Obsidian"])
        keep_instance.all.return_value = [note]

        sync_keep(config)

        # The synced label should have been added to the note
        note.labels.add.assert_called_with(synced_label)
        # And changes should have been pushed back to Keep
        keep_instance.sync.assert_called_once()


@patch("obsidian_syncer.keep.gkeepapi.Keep")
def test_sync_keep_skips_without_required_tags(MockKeep):
    """Notes missing required tags are not synced."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _make_config(tags=["Obsidian"], target_folder=tmpdir)

        keep_instance = MockKeep.return_value
        keep_instance.authenticate.return_value = True
        keep_instance.labels.return_value = []
        keep_instance.findLabel.return_value = None

        note = _make_mock_note(title="No Match", labels=["OtherTag"])
        keep_instance.all.return_value = [note]

        sync_keep(config)

        assert not os.path.exists(os.path.join(tmpdir, "No Match.md"))


@patch("obsidian_syncer.keep.gkeepapi.Keep")
def test_sync_keep_auth_failure_aborts(MockKeep):
    """If authentication fails, no notes are processed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _make_config(target_folder=tmpdir)

        keep_instance = MockKeep.return_value
        keep_instance.authenticate.side_effect = gkeepapi.exception.LoginException(
            "BadAuthentication"
        )

        sync_keep(config)

        keep_instance.all.assert_not_called()


@patch("obsidian_syncer.keep.gkeepapi.Keep")
def test_sync_keep_atomic_write(MockKeep):
    """Files are written atomically (no .tmp files left behind)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = _make_config(tags=["Obsidian"], target_folder=tmpdir)

        keep_instance = MockKeep.return_value
        keep_instance.authenticate.return_value = True
        keep_instance.labels.return_value = []
        keep_instance.findLabel.return_value = None

        note = _make_mock_note(title="Atomic", labels=["Obsidian"])
        keep_instance.all.return_value = [note]

        sync_keep(config)

        # Final file should exist, no .tmp file should remain
        assert os.path.exists(os.path.join(tmpdir, "Atomic.md"))
        tmp_files = [f for f in os.listdir(tmpdir) if f.endswith(".tmp")]
        assert len(tmp_files) == 0

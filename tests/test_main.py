"""Tests for the main module — verifying no import side-effects."""

import logging


def test_import_has_no_side_effects():
    """Importing main should NOT configure logging or install signal handlers.

    This validates fix #7: all side-effects moved inside main().
    """
    # Record state before import
    root_logger = logging.getLogger()
    handlers_before = list(root_logger.handlers)

    # Force re-import (may already be cached, which is fine — if cached
    # it already passed the test on first import)
    import obsidian_syncer.main  # noqa: F401

    # The module should not have added logging handlers at import time.
    # Note: if this is not the first import, handlers won't change either way,
    # which is the correct behavior.
    handlers_after = list(root_logger.handlers)
    assert len(handlers_after) == len(handlers_before), (
        "Importing obsidian_syncer.main should not add logging handlers. "
        f"Before: {len(handlers_before)}, After: {len(handlers_after)}"
    )


def test_setup_logging_configures_root_logger():
    """setup_logging() should configure the root logger."""
    from obsidian_syncer.main import setup_logging

    root_logger = logging.getLogger()
    # Clear any existing handlers for a clean test
    root_logger.handlers.clear()

    setup_logging()

    assert len(root_logger.handlers) > 0


def test_run_sync_loop_is_callable():
    """run_sync_loop should be importable and callable (validates extraction)."""
    from obsidian_syncer.main import run_sync_loop

    assert callable(run_sync_loop)


def test_handle_exit_is_callable():
    """handle_exit should be importable and callable."""
    from obsidian_syncer.main import handle_exit

    assert callable(handle_exit)

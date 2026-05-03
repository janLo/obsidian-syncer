import os
import tempfile
from unittest.mock import MagicMock
from datetime import datetime
import pytest
import gkeepapi

from obsidian_syncer.keep import (
    extract_inline_tags,
    should_sync_note,
    has_gemini_link,
    format_note_content,
    save_note_to_disk,
    get_or_create_label,
)

def test_extract_inline_tags():
    # Test tags line
    text = "Some text\nLabels: test1, test2 test3"
    assert extract_inline_tags(text) == ["test1", "test2", "test3"]

    # Test hashtags
    text2 = "Some text\n#hashtag1 #tag_with_underscore #tag-with-dash"
    assert extract_inline_tags(text2) == ["hashtag1", "tag_with_underscore", "tag-with-dash"]

    # Test combination
    text3 = "Hello\nLabels: my_label\n#my_tag"
    assert extract_inline_tags(text3) == ["my_label", "my_tag"]
    
    # Test no tags
    text4 = "Just regular text\nNo tags here."
    assert extract_inline_tags(text4) == []

def test_should_sync_note():
    # Required subset matches, no ignore matches -> True
    assert should_sync_note({"tag1", "tag2"}, {"tag1"}, {"ignore1"}) == True
    
    # Required subset does not match -> False
    assert should_sync_note({"tag2"}, {"tag1"}, {"ignore1"}) == False
    
    # Required matches, but ignore matches -> False
    assert should_sync_note({"tag1", "ignore1"}, {"tag1"}, {"ignore1"}) == False

def test_has_gemini_link():
    # Mock node
    note = MagicMock(spec=gkeepapi.node.Note)
    
    # No annotations
    note.annotations = None
    assert has_gemini_link(note) == False

    # WebLink, but not Gemini
    ann = MagicMock(spec=gkeepapi.node.WebLink)
    ann.url = "https://example.com"
    
    note.annotations = MagicMock()
    note.annotations.all.return_value = [ann]
    assert has_gemini_link(note) == False

    # Gemini WebLink
    ann_gemini = MagicMock(spec=gkeepapi.node.WebLink)
    ann_gemini.url = "https://gemini.google.com/test"
    note.annotations.all.return_value = [ann_gemini]
    assert has_gemini_link(note) == True

def test_format_note_content():
    note = MagicMock(spec=gkeepapi.node.Note)
    note.title = "Test Note"
    note.text = "This is a test note."
    note.timestamps.created = datetime(2023, 1, 1, 12, 0, 0)
    
    content = format_note_content(note, {"tagA", "tagB"})
    
    assert "---\ncreated: 2023-01-01T12:00:00" in content
    assert "tags:" in content
    assert "  - tagA" in content
    assert "  - tagB" in content
    assert "# Test Note" in content
    assert "This is a test note." in content

def test_save_note_to_disk():
    note = MagicMock(spec=gkeepapi.node.Note)
    note.title = "A ? Test : Note!"
    note.id = "123"
    
    content = "Hello World"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        filename = save_note_to_disk(note, content, tmpdir)
        assert filename == "A  Test  Note.md"
        
        filepath = os.path.join(tmpdir, filename)
        assert os.path.exists(filepath)
        with open(filepath, "r") as f:
            assert f.read() == content

def test_save_note_to_disk_empty_title():
    note = MagicMock(spec=gkeepapi.node.Note)
    note.title = ""
    note.id = "123"
    
    content = "Hello World"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        filename = save_note_to_disk(note, content, tmpdir)
        assert filename == "Note_123.md"

def test_get_or_create_label():
    keep = MagicMock(spec=gkeepapi.Keep)
    # 1. Exact match found
    lbl = MagicMock()
    keep.findLabel.return_value = lbl
    assert get_or_create_label(keep, "Test") == lbl
    
    # 2. Case-insensitive match found
    keep.findLabel.return_value = None
    existing_lbl = MagicMock()
    existing_lbl.name = "test"
    keep.labels.return_value = [existing_lbl]
    assert get_or_create_label(keep, "Test") == existing_lbl
    
    # 3. Not found, create
    keep.labels.return_value = []
    created_lbl = MagicMock()
    keep.createLabel.return_value = created_lbl
    assert get_or_create_label(keep, "Test") == created_lbl
    keep.createLabel.assert_called_once_with("Test")

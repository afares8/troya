"""Tests for cascade/bookmarks.py."""

import tempfile
from pathlib import Path
from unittest import TestCase

from cascade.bookmarks import BookmarkManager


class TestBookmarks(TestCase):
    def setUp(self):
        self.bm = BookmarkManager()
        # Clear any existing bookmarks
        self.bm.bookmarks = []
        self.bm._save()

    def tearDown(self):
        self.bm.bookmarks = []
        self.bm._save()

    def test_add_bookmark(self):
        self.bm.add("test_func", Path("/tmp/test.py"), 10)
        self.assertEqual(len(self.bm.bookmarks), 1)
        self.assertEqual(self.bm.bookmarks[0]["name"], "test_func")

    def test_get_bookmark(self):
        self.bm.add("auth", Path("/tmp/auth.py"), 5, "Auth handler")
        result = self.bm.jump("auth")
        self.assertIsNotNone(result)
        self.assertEqual(result["line"], 5)

    def test_remove_bookmark(self):
        self.bm.add("todo", Path("/tmp/todo.py"))
        self.assertTrue(self.bm.remove("todo"))
        self.assertEqual(len(self.bm.bookmarks), 0)
        self.assertFalse(self.bm.remove("nonexistent"))

    def test_list_empty(self):
        self.bm.bookmarks = []
        result = self.bm.list()
        self.assertEqual(len(result), 0)

"""Tests for cascade/snippets.py."""

from unittest import TestCase

from cascade.snippets import SnippetManager


class TestSnippets(TestCase):
    def setUp(self):
        self.sm = SnippetManager()
        self.sm.snippets = {}
        self.sm._save()

    def tearDown(self):
        self.sm.snippets = {}
        self.sm._save()

    def test_add_and_get(self):
        self.sm.add("fibonacci", "def fib(n): return n if n < 2 else fib(n-1)+fib(n-2)")
        snippet = self.sm.get("fibonacci")
        self.assertIsNotNone(snippet)
        self.assertIn("def fib", snippet["code"])

    def test_search(self):
        self.sm.add("auth", "def login(): pass", "python", ["auth"])
        self.sm.add("sort", "def quicksort(): pass", "python", ["algo"])
        results = self.sm.search("auth")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "auth")

    def test_remove(self):
        self.sm.add("temp", "x = 1")
        self.assertTrue(self.sm.remove("temp"))
        self.assertIsNone(self.sm.get("temp"))
        self.assertFalse(self.sm.remove("temp"))

    def test_list_all(self):
        self.sm.add("a", "code1")
        self.sm.add("b", "code2")
        self.assertEqual(len(self.sm.list_all()), 2)

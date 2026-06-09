"""Tests for cascade/memory.py."""

from unittest import TestCase

from cascade.memory import MemoryStore


class TestMemory(TestCase):
    def setUp(self):
        self.store = MemoryStore()
        # Clear
        self.store.data = {"corrections": [], "preferences": {}, "facts": [], "patterns": {}}
        self.store._save()

    def tearDown(self):
        self.store.data = {"corrections": [], "preferences": {}, "facts": [], "patterns": {}}
        self.store._save()

    def test_add_correction(self):
        self.store.add_correction("old code", "new code", "fix typo")
        self.assertEqual(len(self.store.data["corrections"]), 1)

    def test_preference(self):
        self.store.set_preference("theme", "dark", project="test")
        self.assertEqual(self.store.get_preference("theme", "test"), "dark")
        self.assertEqual(self.store.get_preference("theme", "other", "light"), "light")

    def test_facts(self):
        self.store.add_fact("auth", "Uses JWT tokens")
        facts = self.store.find_facts("JWT")
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["subject"], "auth")

    def test_relevant_context(self):
        self.store.set_preference("indent", "spaces", "global")
        self.store.add_fact("db", "Postgres on port 5432")
        ctx = self.store.get_relevant_context("database config", "global")
        self.assertIn("preferences", ctx)

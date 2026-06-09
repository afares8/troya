"""Tests for cascade/skills.py."""

from unittest import TestCase

from cascade.skills import SkillManager


class TestSkills(TestCase):
    def setUp(self):
        self.sm = SkillManager()
        self.sm.skills = {}
        self.sm._save()

    def tearDown(self):
        self.sm.skills = {}
        self.sm._save()

    def test_learn_skill(self):
        self.sm.learn_skill("fastapi-auth", "JWT pattern", "auth context", ["example1"])
        self.assertIn("fastapi-auth", self.sm.skills)
        self.assertEqual(self.sm.skills["fastapi-auth"]["uses"], 0)

    def test_get_skill_updates_uses(self):
        self.sm.learn_skill("test", "pattern", "ctx")
        skill = self.sm.get_skill("test")
        self.assertIsNotNone(skill)
        self.assertEqual(skill["uses"], 1)

    def test_find_relevant(self):
        self.sm.learn_skill("auth-jwt", "JWT", "authentication")
        self.sm.learn_skill("db-postgres", "SQL", "database")
        results = self.sm.find_relevant("auth")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "auth-jwt")

    def test_list_skills(self):
        self.sm.learn_skill("a", "p1", "c1")
        self.sm.learn_skill("b", "p2", "c2")
        skills = self.sm.list_skills()
        self.assertEqual(len(skills), 2)

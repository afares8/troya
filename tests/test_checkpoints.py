"""Tests for cascade/checkpoints.py."""

from unittest import TestCase

from cascade.checkpoints import CheckpointManager


class TestCheckpoints(TestCase):
    def tearDown(self):
        import shutil
        from cascade.checkpoints import CHECKPOINT_DIR
        if CHECKPOINT_DIR.exists():
            for f in CHECKPOINT_DIR.glob("test_*.json"):
                f.unlink()

    def test_create_and_save(self):
        cp = CheckpointManager("test_task_1")
        cp.update(objective="Test objective", current_step=2)
        self.assertEqual(cp.data["objective"], "Test objective")
        self.assertEqual(cp.data["current_step"], 2)

    def test_add_result(self):
        cp = CheckpointManager("test_task_2")
        cp.add_result({"success": True, "step": 1})
        self.assertEqual(len(cp.data["results"]), 1)
        self.assertTrue(cp.data["results"][0]["success"])

    def test_mark_complete(self):
        cp = CheckpointManager("test_task_3")
        cp.mark_complete()
        self.assertEqual(cp.data["status"], "completed")

    def test_load_checkpoint(self):
        cp = CheckpointManager("test_task_4")
        cp.update(objective="Load test")
        loaded = CheckpointManager.load_checkpoint("test_task_4")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.data["objective"], "Load test")

    def test_list_checkpoints(self):
        cp = CheckpointManager("test_task_5")
        cp.save()
        checkpoints = CheckpointManager.list_checkpoints()
        ids = [c[0] for c in checkpoints]
        self.assertIn("test_task_5", ids)

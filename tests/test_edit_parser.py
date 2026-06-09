"""Tests for cascade/edit_parser.py."""

from pathlib import Path
from unittest import TestCase

from cascade.edit_parser import EditParser, extract_code_blocks


class TestEditParser(TestCase):
    def test_parse_file_blocks(self):
        text = """```python @test.py
def hello():
    pass
```"""
        edits = EditParser.parse(text)
        self.assertTrue(any(e["file"] == "test.py" for e in edits))

    def test_parse_search_replace(self):
        text = """SEARCH:
old_text
REPLACE:
new_text
"""
        edits = EditParser._parse_search_replace(text)
        self.assertGreaterEqual(len(edits), 1)
        self.assertIn("old_text", edits[0]["old"])

    def test_extract_code_blocks(self):
        text = """```python
def foo():
    pass
```

```javascript
console.log("hi");
```"""
        blocks = extract_code_blocks(text)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["language"], "python")
        self.assertEqual(blocks[1]["language"], "javascript")

    def test_apply_create_edit(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            edits = [{"type": "create", "file": "new.py", "content": "x = 1\n"}]
            result = EditParser.apply_edits(edits, Path(td))
            self.assertEqual(result["applied"], 1)
            self.assertTrue((Path(td) / "new.py").exists())

"""Regression checks for preserving user edits during automatic refreshes."""
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import update_profile as profile


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.readme = (profile.ROOT / 'README.md').read_text()
        self.values = {key: 'Updated data for ' + key for key in profile.BLOCK_NAMES}

    def outside_blocks(self, content):
        return re.sub(r'(?s)(<!-- AUTO:[\w-]+:START -->).*?(<!-- AUTO:[\w-]+:END -->)', r'\1\2', content)

    def test_refresh_preserves_all_personal_text_and_layout(self):
        edited = self.readme.replace('## Selected projects', "My new note: I am trying something different.\n\n## Selected projects")
        result = profile.replace_blocks(edited, self.values)
        self.assertEqual(self.outside_blocks(edited), self.outside_blocks(result))
        self.assertIn('My new note:', result)
        self.assertIn('<table>', result)
        self.assertIn('## Around the repos', result)
        self.assertIn('## At the keyboard', result)

    def test_repeating_refresh_is_idempotent(self):
        once = profile.replace_blocks(self.readme, self.values)
        self.assertEqual(once, profile.replace_blocks(once, self.values))

    def test_missing_duplicate_and_reversed_markers_are_rejected(self):
        start = '<!-- AUTO:coding-time:START -->'
        end = '<!-- AUTO:coding-time:END -->'
        cases = [self.readme.replace(start, ''), self.readme + start,
                 self.readme.replace(start, 'TEMP').replace(end, start).replace('TEMP', end)]
        for content in cases:
            with self.subTest(content=content[:30]), self.assertRaises(ValueError):
                profile.replace_blocks(content, self.values)

    def test_provider_failure_preserves_saved_snapshot_exactly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'example.json'
            original = '{"updated": "2026-09-04", "total": 42}\n'
            path.write_text(original)
            with patch.object(profile, 'ASSETS', Path(directory)):
                def unavailable():
                    raise OSError('provider unavailable')
                with patch('builtins.print'):
                    result = profile.cached('example', unavailable, True)
            self.assertEqual(result, json.loads(original))
            self.assertEqual(path.read_text(), original)

    def test_broken_markers_do_not_write_readme_or_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = self.readme.replace('<!-- AUTO:blog-posts:END -->', '')
            (root / 'README.md').write_text(content)
            with patch.object(profile, 'ROOT', root), patch.object(profile, 'ASSETS', root / 'assets'):
                with self.assertRaises(ValueError):
                    profile.render({}, {}, [])
            self.assertEqual((root / 'README.md').read_text(), content)
            self.assertFalse((root / 'assets').exists())


if __name__ == '__main__':
    unittest.main()

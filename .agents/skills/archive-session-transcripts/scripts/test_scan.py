"""Synthetic discovery tests; no real transcript content is read."""
import tempfile
import unittest
from pathlib import Path

from scan import scan


class ScanTests(unittest.TestCase):
    def test_formats_and_exclusions_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixtures = {
                "export.md": "## User\nInvestigate.\n## Assistant\nVerified.\n",
                "messages.jsonl": '{"type":"user","message":{"role":"user","content":"Inspect"}}\n',
                "rollout.jsonl": '{"type":"session_meta","payload":{"cwd":"example"}}\n',
                "README.md": "# Project\nOrdinary documentation.\n",
                "docs/export.md": "User: inspect\nAssistant: done\n",
                "node_modules/chat.txt": "User: inspect\nAssistant: done\n",
                "secrets.json": '{"role":"user","content":"synthetic"}',
            }
            for relative, content in fixtures.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            result = scan(root)
            self.assertEqual({c["path"] for c in result["candidates"]},
                             {"export.md", "messages.jsonl", "rollout.jsonl"})
            self.assertFalse(result["errors"])
            self.assertIn("docs/export.md", {c["path"] for c in scan(root, include_docs=True)["candidates"]})
            after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)

    def test_malformed_sample_and_filename_are_only_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "transcript-broken.jsonl").write_text('{"broken":', encoding="utf-8")
            result = scan(root)
            self.assertEqual(result["candidates"][0]["reason"], "filename-only-review-required")

    def test_claude_terminal_cursor_markdown_and_codex_variants(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "2026-10-01-123456-review.txt").write_text(
                '\x1b[32m> inspect\x1b[0m\n\u25cf Reviewing\n\u23bf command output\n', encoding="utf-8")
            (root / "codex-session-12345678-1234-1234-1234-123456789abc_2.md").write_text(
                '# Session\n## User\nInspect\n## Assistant\n## Activity\nDone\n', encoding="utf-8")
            (root / "native.jsonl").write_text(
                '{"type":"response_item","payload":{"type":"message","role":"assistant","content":[{"type":"output_text","text":"done"}]}}\n', encoding="utf-8")
            (root / "export.json").write_text(
                '{"messages":[{"role":"user","content":"inspect"},{"role":"assistant","content":"done"}]}', encoding="utf-8")
            result = scan(root)
            self.assertEqual(len(result["candidates"]), 4)
            self.assertIn("claude-terminal-dialogue", {c["reason"] for c in result["candidates"]})

    def test_near_misses_and_staging_are_not_transcripts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "export_support_bundle.md").write_text('# Export\nA procedure.', encoding="utf-8")
            (root / "2026-06-20_134808_summary.json").write_text('{"bytes":123}', encoding="utf-8")
            (root / "2025_Wage_Income_Transcript_text.txt").write_text('Tax document', encoding="utf-8")
            staging = root / "local/kb-staging"
            staging.mkdir(parents=True)
            (staging / "part-001.md").write_text('User: inspect\nAssistant: done\n', encoding="utf-8")
            self.assertEqual(scan(root)["candidates"], [])

    def test_embedded_examples_do_not_promote_artifacts_to_dialogue(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            example = '## User\nExample prompt\n## Assistant\nExample response\n'
            (root / 'guide.md').write_text('```md\n' + example + '```\n', encoding='utf-8')
            (root / 'scores.md').write_text('<INSTRUCTIONS>\n' + example + '</INSTRUCTIONS>', encoding='utf-8')
            (root / 'context.txt').write_text('<system-reminder>\n> synthetic\n● synthetic\n', encoding='utf-8')
            (root / 'transcript-review.md').write_text('~~~~md\n' + example + '~~~~\n', encoding='utf-8')
            (root / 'actual.md').write_text('```md\n' + example + '```\n' + example, encoding='utf-8')
            result = scan(root)
            found = {c['path']: c for c in result['candidates']}
            self.assertEqual(set(found), {'actual.md', 'transcript-review.md'})
            self.assertEqual(found['actual.md']['reason'], 'dialogue-markers')
            self.assertEqual(found['transcript-review.md']['confidence'], 'low')

    def test_date_only_scratch_exports_remain_visible_with_sample_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / '.agent/scratch/exports/2026-10-05-image-formats.md'
            path.parent.mkdir(parents=True)
            original = b'# Cursor chat export\n## User\nInspect formats.\n## Assistant\nFound support.\n' + b'x' * 200
            path.write_bytes(original)
            (path.parent / '2026-10-05-plan.md').write_text('# Plan\nOrdinary prose.', encoding='utf-8')
            result = scan(root, sample_bytes=100)
            self.assertEqual(len(result['candidates']), 1)
            candidate = result['candidates'][0]
            self.assertEqual(candidate['path'], path.relative_to(root).as_posix())
            self.assertTrue(candidate['sample_truncated'])
            self.assertEqual(candidate['bytes'], len(original))
            self.assertEqual(path.read_bytes(), original)

    def test_invalid_root_and_link_do_not_expand_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(OSError):
                scan(root / "missing")
            (root / "file.txt").write_text("ordinary", encoding="utf-8")
            with self.assertRaises(ValueError):
                scan(root / "file.txt")
            try:
                (root / "linked").symlink_to(root, target_is_directory=True)
            except OSError:
                return  # Windows may not grant symlink creation.
            with self.assertRaises(ValueError):
                scan(root / "linked")


if __name__ == "__main__":
    unittest.main()

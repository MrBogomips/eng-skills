"""End-to-end tests for skills/docs-impact/scripts/docs_impact.py."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "skills" / "docs-impact" / "scripts" / "docs_impact.py"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false"]


class CliTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        self.git("init", "-q", "-b", "main")

    def git(self, *args):
        subprocess.run([*GIT, *args], cwd=self.repo, check=True, capture_output=True)

    def write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def seed(self):
        self.write("src/cli.py", 'parser.add_argument("--out")\n')
        self.write("docs/usage.md", "# Usage\n\nPass --out to choose the folder.\n")
        self.commit("base")
        self.git("checkout", "-q", "-b", "feature/x")

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(CLI), "--repo", str(self.repo), *args],
            capture_output=True, text=True,
        )

    def test_cli_end_to_end_md(self):
        self.seed()
        self.write("src/cli.py", 'parser.add_argument("--output-dir")\nparser.add_argument("--fresh")\n')
        self.write("docs/extra.md", "# Extra\n")
        self.commit("rename flag")
        proc = self.run_cli()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout
        self.assertIn("docs/usage.md#usage", out)
        self.assertIn("update", out)
        self.assertIn("--fresh", out)
        self.assertIn("## Review context", out)

    def test_cli_no_impact_exit_0(self):
        self.seed()
        self.write("README.md", "# Hello\n")
        self.commit("docs only")
        proc = self.run_cli()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("No documentation impact found.", proc.stdout)

    def test_cli_missing_base_exit_2_with_fetch_hint(self):
        self.seed()
        proc = self.run_cli("--base", "nope/missing")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("nope/missing", proc.stderr)
        self.assertIn("git fetch origin", proc.stderr)
        self.assertEqual(len(proc.stderr.strip().splitlines()), 1)

    def test_cli_default_base_falls_back_to_main(self):
        self.seed()
        self.write("src/cli.py", 'parser.add_argument("--output-dir")\n')
        self.commit("rename")
        data = json.loads(self.run_cli("--format", "json").stdout)
        self.assertEqual(data["base"], "main")

    def test_cli_bad_arguments_exit_2(self):
        self.seed()
        self.assertEqual(self.run_cli("--map", "nonsense").returncode, 2)
        self.assertEqual(self.run_cli("--max-impacts", "-1").returncode, 2)

    def test_cli_out_file_and_max_impacts(self):
        self.write("docs/second.md", "# Second\n\nAlso --out here.\n")
        self.seed()
        self.write("src/cli.py", 'parser.add_argument("--output-dir")\n')
        self.commit("rename")
        target = self.repo / "report-out.md"
        proc = self.run_cli("--max-impacts", "1", "--out", str(target))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(proc.stdout.strip().splitlines()), 1)
        self.assertIn("1 impacts omitted (--max-impacts)", target.read_text(encoding="utf-8"))

    def test_cli_pages_urls_in_report(self):
        self.write("mkdocs.yml", "site_url: https://docs.example.org/w/\n")
        self.write("src/cli.py", 'parser.add_argument("--out")\n')
        self.write("docs/usage.md", "# Usage\n\nPass --out to choose the folder.\n")
        self.commit("base")
        self.git("checkout", "-q", "-b", "feature/x")
        self.write("src/cli.py", 'parser.add_argument("--output-dir")\n')
        self.commit("rename")
        out = self.run_cli().stdout
        self.assertIn("https://docs.example.org/w/usage/#usage", out)
        off = self.run_cli("--pages", "off").stdout
        self.assertNotIn("docs.example.org", off)

    def test_cli_nav_lists_page_url(self):
        self.write("mkdocs.yml", "site_name: P\nsite_url: https://example.github.io/pixkit/\nnav:\n  - Home: index.md\n")
        self.write("docs/index.md", "# Home\n")
        self.commit("base")
        self.git("checkout", "-q", "-b", "feature/x")
        self.write("docs/guides/batch.md", "# Batch\n")
        self.commit("add page")
        out = self.run_cli().stdout
        self.assertIn("docs/guides/batch.md https://example.github.io/pixkit/guides/batch/", out)
        nav = json.loads(self.run_cli("--format", "json").stdout)["navigation"]
        self.assertEqual(nav, [{"path": "docs/guides/batch.md",
                                "url": "https://example.github.io/pixkit/guides/batch/"}])

    def test_cli_updated_sections_leave_impacts(self):
        self.seed()
        self.write("src/cli.py", 'parser.add_argument("--output-dir")\n')
        self.write("docs/usage.md", "# Usage\n\nPass --out to choose the folder.\nEdited.\n")
        self.commit("rename and touch doc")
        out = self.run_cli("--format", "md").stdout
        impacts = out.split("## Impacts")[1].split("## ")[0]
        self.assertNotIn("docs/usage.md", impacts)
        updated = out.split("## Already updated in this branch")[1].split("## ")[0]
        self.assertIn("docs/usage.md#usage (update)", updated)
        self.assertNotIn("docs/usage.md", out.split("## Review context")[1])

    def test_main_in_process_writes_out_file(self):
        sys.path.insert(0, str(CLI.parent))
        import docs_impact
        self.seed()
        self.write("src/cli.py", 'parser.add_argument("--output-dir")\n')
        self.commit("rename")
        target = self.repo / "r.json"
        argv = ["--repo", str(self.repo), "--format", "json", "--out", str(target)]
        self.assertEqual(docs_impact.main(argv), 0)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["base"], "main")
        self.assertEqual(docs_impact.main(["--repo", str(self.repo), "--base", "zzz"]), 2)


if __name__ == "__main__":
    unittest.main()

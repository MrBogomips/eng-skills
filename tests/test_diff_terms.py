"""Tests for skills/docs-impact/scripts/diff_terms.py."""

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "docs-impact" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import diff_terms  # noqa: E402
from diff_terms import Term  # noqa: E402


def diff(path, removed=(), added=(), header=None):
    """Build a unified=0 diff for one file."""
    lines = header or [f"diff --git a/{path} b/{path}", f"--- a/{path}", f"+++ b/{path}"]
    lines.append(f"@@ -1,{len(removed)} +1,{len(added)} @@")
    lines += [f"-{r}" for r in removed] + [f"+{a}" for a in added]
    return "\n".join(lines) + "\n"


def by_text(terms):
    return {t.text: t.change for t in terms}


class ParseDiffTest(unittest.TestCase):
    def test_renamed_flag_is_changed_pair(self):
        terms = diff_terms.parse_diff(diff(
            "cli.py",
            removed=['p.add_argument("--output-dir")'],
            added=['p.add_argument("--out-dir")']))
        got = by_text(terms)
        self.assertEqual(got["--output-dir"], "removed")
        self.assertEqual(got["--out-dir"], "added")
        self.assertTrue(all(t.kind == "flag" and t.file == "cli.py" for t in terms))

    def test_flag_on_both_sides_is_changed(self):
        terms = diff_terms.parse_diff(diff(
            "cli.py", removed=['add("--verbose", help="a")'], added=['add("--verbose", help="b")']))
        self.assertEqual(by_text(terms)["--verbose"], "changed")

    def test_private_python_def_ignored(self):
        terms = diff_terms.parse_diff(diff(
            "m.py", added=["def _helper(x):", "def render_page(x):", "class Widget:"]))
        got = by_text(terms)
        self.assertNotIn("_helper", got)
        self.assertEqual(got["render_page"], "added")
        self.assertEqual(got["Widget"], "added")

    def test_go_exported_func_only(self):
        terms = diff_terms.parse_diff(diff(
            "a.go", added=["func Cancel(o *Order) error {", "func cancelInternal() {", "type Order struct {"]))
        got = by_text(terms)
        self.assertIn("Cancel", got)
        self.assertIn("Order", got)
        self.assertNotIn("cancelInternal", got)

    def test_env_var_removed(self):
        terms = diff_terms.parse_diff(diff(
            "cfg.py", removed=['os.environ["APP_TOKEN_TTL"]', 'os.getenv("APP_REGION")'], added=[]))
        got = by_text(terms)
        self.assertEqual(got["APP_TOKEN_TTL"], "removed")
        self.assertEqual(got["APP_REGION"], "removed")
        self.assertTrue(all(t.kind == "env" for t in terms))

    def test_yaml_key_changed(self):
        terms = diff_terms.parse_diff(diff(
            "conf.yaml", removed=["  retry_limit: 3"], added=["  retry_limit: 5"]))
        self.assertEqual(terms, [Term("retry_limit", "config_key", "changed", "conf.yaml", 1)])

    def test_short_and_stoplisted_terms_dropped(self):
        terms = diff_terms.parse_diff(diff(
            "m.py", added=["def run(x):", "def main():", "def data():", "def init():"]))
        self.assertEqual(terms, [])

    def test_test_files_skipped(self):
        for path in ("tests/foo.py", "test_x.py", "x_test.go", "src/__tests__/a.ts"):
            terms = diff_terms.parse_diff(diff(path, added=["def render_page(x):"]))
            self.assertEqual(terms, [], path)

    def test_binary_diff_skipped(self):
        text = ("diff --git a/logo.png b/logo.png\nindex 1..2 100644\n"
                "Binary files a/logo.png and b/logo.png differ\n")
        self.assertEqual(diff_terms.parse_diff(text), [])

    def test_route_extracted(self):
        terms = diff_terms.parse_diff(diff("app.py", added=['@app.get("/api/orders/list")']))
        self.assertIn(Term("/api/orders/list", "route", "added", "app.py", 1), terms)

    def test_rename_yields_path_terms(self):
        text = textwrap.dedent("""\
            diff --git a/docs/old_name.md b/docs/new_name.md
            similarity index 100%
            rename from docs/old_name.md
            rename to docs/new_name.md
            """)
        got = {(t.text, t.kind, t.change) for t in diff_terms.parse_diff(text)}
        self.assertIn(("docs/old_name.md", "path", "removed"), got)
        self.assertIn(("docs/new_name.md", "path", "added"), got)


def git(repo, *args):
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=repo, check=True, capture_output=True, text=True)


class GitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-b", "main")
        (self.repo / "cli.py").write_text('add("--output-dir")\n')
        (self.repo / "old.txt").write_text("hello world\n" * 5)
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "base")
        git(self.repo, "checkout", "-b", "topic")
        (self.repo / "cli.py").write_text('add("--out-dir")\n')
        git(self.repo, "mv", "old.txt", "new.txt")
        git(self.repo, "commit", "-am", "change")

    def test_extract_terms_from_repo(self):
        got = by_text(diff_terms.extract_terms(self.repo, "main"))
        self.assertEqual(got["--output-dir"], "removed")
        self.assertEqual(got["--out-dir"], "added")

    def test_changed_files(self):
        got = diff_terms.changed_files(self.repo, "main")
        self.assertIn(("M", "cli.py", None), got)
        self.assertIn(("R", "new.txt", "old.txt"), got)

    def test_bad_base_raises_git_error(self):
        with self.assertRaises(diff_terms.GitError):
            diff_terms.extract_terms(self.repo, "nope")
        with self.assertRaises(diff_terms.GitError):
            diff_terms.changed_files(self.repo, "nope")


if __name__ == "__main__":
    unittest.main()

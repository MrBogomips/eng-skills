"""Regression tests for the final whole-branch review of docs-impact."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "docs-impact" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import diff_terms  # noqa: E402
from diff_terms import Term  # noqa: E402
from doc_sections import Section  # noqa: E402
from impact import match, undocumented  # noqa: E402
from pages import PagesSite, page_url  # noqa: E402

CLI = SCRIPTS / "docs_impact.py"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false"]


def sec(text, path="docs/usage.md", anchor="usage", start=1, end=6):
    return Section(path, anchor, anchor.title(), start, end, text)


class RepoCase(unittest.TestCase):
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

    def cli(self, *args):
        return subprocess.run([sys.executable, str(CLI), "--repo", str(self.repo), *args],
                              capture_output=True, text=True)


class OutExcludedTest(RepoCase):  # I1
    def test_report_saved_in_repo_is_not_scanned_next_run(self):
        self.write("src/cli.py", 'parser.add_argument("--out")\n')
        self.write("docs/usage.md", "# Usage\n\nPass --out.\n")
        self.commit("base")
        self.git("checkout", "-q", "-b", "f")
        self.write("src/cli.py", 'parser.add_argument("--output-dir")\n')
        self.commit("rename")
        self.assertEqual(self.cli("--out", str(self.repo / "DOCS-IMPACT.md")).returncode, 0)
        proc = self.cli("--out", str(self.repo / "DOCS-IMPACT.md"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        text = (self.repo / "DOCS-IMPACT.md").read_text(encoding="utf-8")
        self.assertNotIn("DOCS-IMPACT.md#", text)


class ToolingConfigTest(unittest.TestCase):  # I2
    def test_ci_and_tooling_files_yield_no_config_keys(self):
        for path in (".github/workflows/ci.yml", ".gitlab-ci.yml", ".circleci/config.yml",
                     ".pre-commit-config.yaml", "Dockerfile.dev", "docker-compose.yml",
                     "compose.yaml"):
            hdr = [f"diff --git a/{path} b/{path}", f"--- a/{path}", f"+++ b/{path}",
                   "@@ -1,1 +1,0 @@", "-    with: something"]
            self.assertEqual(diff_terms.parse_diff("\n".join(hdr) + "\n"), [], path)

    def test_app_config_still_yields_keys(self):
        hdr = ["diff --git a/config/app.yml b/config/app.yml", "--- a/config/app.yml",
               "+++ b/config/app.yml", "@@ -1,1 +1,0 @@", "-timeout_seconds: 5"]
        self.assertEqual(len(diff_terms.parse_diff("\n".join(hdr) + "\n")), 1)


class MovedTest(unittest.TestCase):  # I3
    def test_cross_file_move_is_neither_obsolete_nor_undocumented(self):
        old = Term("create_refund", "symbol", "removed", "src/api.py", 10)
        new = Term("create_refund", "symbol", "added", "src/refund_ops.py", 3)
        self.assertEqual(match([old, new], [sec("Call create_refund.")], [], []), [])
        self.assertEqual(undocumented([old, new], [sec("nothing")]), [])


class PerSectionUpdatedTest(RepoCase):  # I4
    def test_hunks_overlap_decides(self):
        terms = [Term("--legacy", "flag", "removed", "src/cli.py", 1)]
        a, b = sec("Use --legacy.", anchor="a", start=1, end=5), sec(
            "Use --legacy.", anchor="b", start=6, end=10)
        changed = [("M", "docs/usage.md", None)]
        res = match(terms, [a, b], [], changed, hunks={"docs/usage.md": [(2, 2)]})
        self.assertEqual({i.section.anchor: i.updated_in_branch for i in res},
                         {"a": True, "b": False})

    def test_added_file_all_sections_updated(self):
        terms = [Term("--legacy", "flag", "removed", "src/cli.py", 1)]
        res = match(terms, [sec("Use --legacy.")], [], [("A", "docs/usage.md", None)], hunks={})
        self.assertTrue(res[0].updated_in_branch)

    def test_doc_hunks_from_git(self):
        self.write("docs/usage.md", "# A\n\none\n\n# B\n\ntwo\n")
        self.commit("base")
        self.git("checkout", "-q", "-b", "f")
        self.write("docs/usage.md", "# A\n\none\n\n# B\n\nTWO\n")
        self.commit("edit")
        changed = diff_terms.changed_files(self.repo, "main")
        self.assertEqual(diff_terms.doc_hunks(self.repo, "main", "HEAD", changed),
                         {"docs/usage.md": [(7, 7)]})

    def test_cli_other_section_of_edited_file_still_reported(self):
        self.write("src/cli.py", 'parser.add_argument("--legacy")\n')
        self.write("docs/usage.md", "# One\n\nUse --legacy here.\n\n# Two\n\nTypo.\n")
        self.commit("base")
        self.git("checkout", "-q", "-b", "f")
        self.write("src/cli.py", "\n")
        self.write("docs/usage.md", "# One\n\nUse --legacy here.\n\n# Two\n\nFixed.\n")
        self.commit("remove flag, fix typo elsewhere")
        data = json.loads(self.cli("--format", "json").stdout)
        self.assertEqual([i["anchor"] for i in data["impacts"]], ["one"])


class StaticUrlTest(unittest.TestCase):  # I6
    def test_only_html_gets_url(self):
        site = PagesSite("static", "docs", "https://a.github.io/w/", "actions", None, (), "/x")
        self.assertIsNone(page_url(site, "docs/usage.rst"))
        self.assertIsNone(page_url(site, "docs/usage.md"))
        self.assertEqual(page_url(site, "docs/usage.html"), "https://a.github.io/w/usage.html")


if __name__ == "__main__":
    unittest.main()

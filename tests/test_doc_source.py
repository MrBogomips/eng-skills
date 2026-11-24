"""Tests for skills/docs-impact/scripts/doc_source.py."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "docs-impact" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import doc_source  # noqa: E402
from doc_source import SourceError, resolve_source  # noqa: E402

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false"]


def run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def commit_file(work, name, text):
    (work / name).write_text(text, encoding="utf-8")
    run(["git", "add", name], work)
    run(GIT + ["commit", "-m", "c"], work)


class SourceTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        run(["git", "init", "-b", "main"], self.repo)
        commit_file(self.repo, "README.md", "# repo\n")
        self.work = self.tmp / "work"
        self.work.mkdir()
        run(["git", "init", "-b", "main"], self.work)
        commit_file(self.work, "guide.md", "# v1\n")
        self.bare = self.tmp / "docs.git"
        run(["git", "clone", "--bare", str(self.work), str(self.bare)], self.tmp)
        self.url = self.bare.as_uri()

    def test_none_spec_uses_repo(self):
        res = resolve_source(None, self.repo)
        self.assertEqual(res.root, self.repo)
        self.assertIsNone(res.warning)

    def test_local_path_spec(self):
        res = resolve_source(str(self.work), self.repo)
        self.assertEqual(res.root, self.work)
        self.assertIsNone(res.warning)

    def test_unusable_spec_raises(self):
        with self.assertRaises(SourceError):
            resolve_source("not a path or url", self.repo)

    def test_url_spec_clones_into_common_dir(self):
        res = resolve_source(self.url, self.repo)
        cache = self.repo / ".git" / "docs-impact" / "sources"
        self.assertEqual(res.root.parent, cache)
        self.assertEqual((res.root / "guide.md").read_text(), "# v1\n")
        self.assertIsNone(res.warning)

    def test_second_run_fetches_update(self):
        resolve_source(self.url, self.repo)
        commit_file(self.work, "guide.md", "# v2\n")
        run(["git", "push", str(self.bare), "main"], self.work)
        res = resolve_source(self.url, self.repo)
        self.assertEqual((res.root / "guide.md").read_text(), "# v2\n")
        self.assertIsNone(res.warning)

    def test_ref_is_checked_out(self):
        run(["git", "branch", "rel"], self.work)
        commit_file(self.work, "guide.md", "# main\n")
        run(["git", "push", str(self.bare), "main", "rel"], self.work)
        res = resolve_source(self.url, self.repo, ref="rel")
        self.assertEqual((res.root / "guide.md").read_text(), "# v1\n")

    def test_offline_with_cache_warns(self):
        first = resolve_source(self.url, self.repo)
        self.bare.rename(self.tmp / "moved.git")
        res = resolve_source(self.url, self.repo)
        self.assertEqual(res.root, first.root)
        self.assertTrue(res.warning)
        self.assertTrue((res.root / "guide.md").exists())

    def test_offline_without_cache_raises(self):
        self.bare.rename(self.tmp / "moved.git")
        with self.assertRaises(SourceError):
            resolve_source(self.url, self.repo)

    def test_option_like_ref_or_spec_rejected(self):
        with self.assertRaises(SourceError):
            resolve_source(self.url, self.repo, ref="--upload-pack=x")
        with self.assertRaises(SourceError):
            resolve_source("-u@h:x", self.repo)

    def test_local_file_spec_raises(self):
        with self.assertRaises(SourceError):
            resolve_source(str(self.work / "guide.md"), self.repo)

    def test_ref_with_local_path_warns(self):
        res = resolve_source(str(self.work), self.repo, ref="main")
        self.assertIn("ignored", res.warning)

    def test_timeout_treated_as_unreachable(self):
        orig = doc_source.subprocess.run

        def slow(*a, **k):
            if a[0][1] in ("clone", "fetch"):
                raise doc_source.subprocess.TimeoutExpired(a[0], 1)
            return orig(*a, **k)
        doc_source.subprocess.run = slow
        try:
            with self.assertRaises(SourceError):
                resolve_source(self.url, self.repo)
        finally:
            doc_source.subprocess.run = orig
        first = resolve_source(self.url, self.repo)
        doc_source.subprocess.run = slow
        try:
            res = resolve_source(self.url, self.repo)
        finally:
            doc_source.subprocess.run = orig
        self.assertEqual(res.root, first.root)
        self.assertIn("timed out", res.warning)

    def test_worktree_shares_common_dir_cache(self):
        run(GIT + ["worktree", "add", str(self.tmp / "wt"), "-b", "x"], self.repo)
        res = resolve_source(self.url, self.tmp / "wt")
        self.assertEqual(res.root.parent, self.repo / ".git" / "docs-impact" / "sources")


if __name__ == "__main__":
    unittest.main()

"""Tests for skills/docs-impact/scripts/doc_sections.py."""

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "docs-impact" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import doc_sections  # noqa: E402
from doc_sections import DEFAULT_DOC_GLOBS, DEFAULT_EXCLUDES, split_sections  # noqa: E402


class SplitSectionsTest(unittest.TestCase):
    def test_markdown_headings_and_anchors(self):
        text = "# Title\nintro\n## Output options\nflags here\n"
        secs = split_sections("README.md", text)
        self.assertEqual([s.anchor for s in secs], ["title", "output-options"])
        self.assertEqual(secs[1].title, "Output options")
        self.assertEqual((secs[1].start_line, secs[1].end_line), (3, 4))
        self.assertEqual(secs[1].text, "## Output options\nflags here")
        self.assertEqual(secs[0].path, "README.md")

    def test_anchor_drops_punctuation(self):
        secs = split_sections("a.md", "## The `--out` flag (v2)!\n")
        self.assertEqual(secs[0].anchor, "the---out-flag-v2")

    def test_heading_inside_code_fence_ignored(self):
        text = "# Real\n```sh\n# comment, not a heading\n```\n~~~\n## nor this\n~~~\n## Next\n"
        secs = split_sections("a.md", text)
        self.assertEqual([s.title for s in secs], ["Real", "Next"])

    def test_rst_and_adoc_titles(self):
        rst = "Intro\n=====\ntext\n\nUsage\n-----\nmore\n"
        self.assertEqual([s.title for s in split_sections("a.rst", rst)], ["Intro", "Usage"])
        over = "=====\nTop\n=====\nbody\n"
        self.assertEqual([s.title for s in split_sections("a.rst", over)], ["Top"])
        adoc = "= Doc\n\ntext\n\n== Section Two\nmore\n"
        secs = split_sections("a.adoc", adoc)
        self.assertEqual([s.anchor for s in secs], ["doc", "section-two"])

    def test_html_headings(self):
        html = "<body>\n<h1>Top</h1>\n<p>x</p>\n<h2 id=\"a\">Sub <em>part</em></h2>\n<p>y</p>\n"
        secs = split_sections("a.html", html)
        self.assertEqual([s.title for s in secs], ["", "Top", "Sub part"])
        self.assertEqual(secs[1].start_line, 2)
        self.assertEqual(secs[2].start_line, 4)

    def test_preamble_section(self):
        secs = split_sections("a.md", "badge line\n\n# Head\nx\n")
        self.assertEqual(secs[0].anchor, "")
        self.assertEqual((secs[0].start_line, secs[0].end_line), (1, 2))
        self.assertEqual(secs[1].anchor, "head")

    def test_no_preamble_when_heading_first_and_empty_file(self):
        self.assertEqual(len(split_sections("a.md", "# H\n")), 1)
        self.assertEqual(split_sections("a.md", ""), [])

    def test_duplicate_anchors_get_suffix(self):
        secs = split_sections("a.md", "# A\n# A\n# A\n")
        self.assertEqual([s.anchor for s in secs], ["a", "a-1", "a-2"])


class FindDocFilesTest(unittest.TestCase):
    def make(self, files):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for name, data in files.items():
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data if isinstance(data, bytes) else data.encode())
        return root

    def rel(self, root, found):
        return sorted(p.relative_to(root).as_posix() for p in found)

    def test_excludes_generator_output(self):
        root = self.make({
            "README.md": "x", "CHANGELOG.md": "x", "notes.md": "x", "src/deep.md": "x",
            "docs/guide.md": "x", "docs/img.png": b"\x89PNG", "docs/sub/api.rst": "x",
            "node_modules/pkg/README.md": "x", "docs/build/out.html": "x",
            "site/index.html": "x", ".git/x.md": "x",
        })
        found = doc_sections.find_doc_files(root, DEFAULT_DOC_GLOBS, DEFAULT_EXCLUDES)
        self.assertEqual(self.rel(root, found),
                         ["README.md", "docs/guide.md", "docs/sub/api.rst", "notes.md"])

    def test_custom_globs(self):
        root = self.make({"a/b/c.md": "x", "top.md": "x"})
        found = doc_sections.find_doc_files(root, ["**/*.md"], [])
        self.assertEqual(self.rel(root, found), ["a/b/c.md", "top.md"])

    def test_non_utf8_file_read_with_replacement(self):
        root = self.make({"a.md": b"# T\xff\xfe\nbody\n", "bin.md": b"# x\x00\x01"})
        self.assertIn("T", doc_sections.read_doc(root / "a.md"))
        self.assertIsNone(doc_sections.read_doc(root / "bin.md"))
        self.assertIsNone(doc_sections.read_doc(root / "missing.md"))


if __name__ == "__main__":
    unittest.main()

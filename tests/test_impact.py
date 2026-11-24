"""Tests for skills/docs-impact/scripts/impact.py and report.py."""

import json
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "docs-impact" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from diff_terms import Term  # noqa: E402
from doc_sections import Section  # noqa: E402
from impact import match, parse_mappings, undocumented  # noqa: E402
from report import render  # noqa: E402


def sec(text, path="docs/usage.md", anchor="usage", start=1):
    return Section(path, anchor, anchor.title(), start, start + 5, text)


def term(text, kind="flag", change="removed", file="src/cli.py", line=10):
    return Term(text, kind, change, file, line)


class MatchTest(unittest.TestCase):
    def test_removed_term_is_obsolete_high(self):
        result = match([term("--legacy")], [sec("Use --legacy to run.")], [], [])
        self.assertEqual(len(result), 1)
        self.assertEqual((result[0].adjustment, result[0].confidence), ("obsolete", "high"))

    def test_renamed_flag_is_update_high(self):
        terms = [term("--out"), term("--output-dir", change="added", line=11)]
        result = match(terms, [sec("Pass --out to set the folder.")], [], [])
        self.assertEqual((result[0].adjustment, result[0].confidence), ("update", "high"))

    def test_rename_and_removal_in_one_section_give_two_impacts(self):
        terms = [term("--out"), term("--output-dir", change="added", line=11),
                 term("OLD_ENV", kind="env", line=40)]
        result = match(terms, [sec("Pass --out. Set OLD_ENV too.")], [], [])
        by_adj = {i.adjustment: i for i in result}
        self.assertEqual(set(by_adj), {"update", "obsolete"})
        self.assertEqual([t.text for t in by_adj["update"].terms], ["--out", "--output-dir"][:1])
        self.assertEqual([t.text for t in by_adj["obsolete"].terms], ["OLD_ENV"])

    def test_added_half_of_reported_rename_not_undocumented(self):
        terms = [term("--out"), term("--output-dir", change="added", line=11)]
        self.assertEqual(undocumented(terms, [sec("Pass --out.")]), [])
        self.assertEqual(len(undocumented(terms, [sec("nothing")])), 1)

    def test_flag_not_matched_inside_longer_flag(self):
        result = match([term("--out")], [sec("Only --output-dir exists.")], [], [])
        self.assertEqual(result, [])

    def test_identifier_word_boundaries_and_case(self):
        t = term("load_cfg", kind="symbol")
        self.assertEqual(match([t], [sec("see load_cfg_all and Load_Cfg")], [], []), [])
        self.assertEqual(len(match([t], [sec("call `load_cfg()` first")], [], [])), 1)

    def test_changed_term_is_update_medium(self):
        t = term("timeout", kind="config_key", change="changed")
        result = match([t], [sec("Set timeout in the file.")], [], [])
        self.assertEqual((result[0].adjustment, result[0].confidence), ("update", "medium"))

    def test_declared_mapping_only_is_check_low(self):
        maps = parse_mappings(["src/** => docs/usage.md"])
        result = match([], [sec("nothing relevant")], maps, [("M", "src/a.py", None)])
        self.assertEqual((result[0].adjustment, result[0].confidence), ("check", "low"))
        self.assertTrue(result[0].declared)

    def test_declared_plus_term_is_high(self):
        maps = parse_mappings(["src/** => docs/usage.md"])
        t = term("timeout", kind="config_key", change="changed", file="src/a.py")
        result = match([t], [sec("Set timeout here.")], maps, [("M", "src/a.py", None)])
        self.assertEqual(result[0].confidence, "high")
        self.assertEqual(result[0].adjustment, "update")

    def test_section_changed_in_branch_marked(self):
        changed = [("M", "docs/usage.md", None)]
        result = match([term("--legacy")], [sec("Use --legacy.")], [], changed)
        self.assertTrue(result[0].updated_in_branch)
        result = match([term("--legacy")], [sec("Use --legacy.")], [], changed, docs_in_repo=False)
        self.assertFalse(result[0].updated_in_branch)

    def test_ranking_and_urls(self):
        terms = [term("--legacy"), term("timeout", "config_key", "changed")]
        sections = [sec("timeout", anchor="a"), sec("--legacy and timeout", anchor="b")]
        result = match(terms, sections, [], [], url_for=lambda s: f"u/{s.anchor}")
        self.assertEqual([(i.section.anchor, i.adjustment) for i in result],
                         [("b", "obsolete"), ("a", "update"), ("b", "update")])
        self.assertEqual(result[0].url, "u/b")

    def test_undocumented_added_flag(self):
        added = term("--brand-new", change="added")
        also = term("--known", change="added")
        gone = term("--gone", change="removed")
        out = undocumented([added, also, gone], [sec("the --known flag")])
        self.assertEqual(out, [added])

    def test_parse_mappings_rejects_bad_spec(self):
        with self.assertRaises(ValueError):
            parse_mappings(["no arrow here"])
        self.assertEqual(parse_mappings(["a/** => b.md"]), [("a/**", "b.md")])


def base_report(**over):
    imp = match([term("--legacy")], [sec("Use --legacy.")], [], [])
    done = match([term("--legacy")], [sec("Use --legacy.", path="docs/old.md")], [],
                 [("M", "docs/old.md", None)])
    report = {
        "base": "main", "head": "HEAD", "diffstat": "1 file changed",
        "source": {"origin": "repo", "root": "/r", "warning": None},
        "pages": None, "warnings": [], "impacts": imp, "updated": done, "omitted": 0,
        "undocumented": [term("--new", change="added")],
        "navigation": [{"path": "docs/new.md", "url": None}], "nav_note": None,
        "mappings": [], "changed": [("M", "docs/usage.md", None)],
    }
    report.update(over)
    return report


class RenderTest(unittest.TestCase):
    def test_render_md_sections_in_order(self):
        text = render(base_report(omitted=3), "md")
        heads = ["## Impacts", "## Undocumented additions", "## Navigation",
                 "## Already updated in this branch", "## Review context"]
        positions = [text.index(h) for h in heads]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("docs/usage.md#usage", text)
        self.assertIn("src/cli.py:10", text)
        self.assertIn("- docs/old.md#usage (obsolete)", text)
        self.assertNotIn("docs/old.md#usage |", text)
        self.assertNotIn("open docs/old.md", text)
        self.assertTrue(text.rstrip().endswith("3 impacts omitted (--max-impacts)"))

    def test_render_md_empty(self):
        text = render(base_report(impacts=[], undocumented=[], navigation=[], updated=[]), "md")
        self.assertIn("No documentation impact found.", text)

    def test_render_json_roundtrip(self):
        data = json.loads(render(base_report(), "json"))
        self.assertEqual(data["impacts"][0]["path"], "docs/usage.md")
        self.assertEqual(data["impacts"][0]["terms"][0]["text"], "--legacy")
        self.assertEqual(data["undocumented"][0]["text"], "--new")
        self.assertEqual(data["navigation"], [{"path": "docs/new.md", "url": None}])
        self.assertEqual(data["updated"][0]["path"], "docs/old.md")

    def test_render_rejects_unknown_format(self):
        with self.assertRaises(ValueError):
            render(base_report(), "xml")


if __name__ == "__main__":
    unittest.main()

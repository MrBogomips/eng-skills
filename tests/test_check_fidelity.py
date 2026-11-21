"""Tests for skills/technical-writing/scripts/check_fidelity.py."""

import io
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "technical-writing" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import check_fidelity  # noqa: E402


def items(text, kind=None):
    found = check_fidelity.extract(textwrap.dedent(text))
    return [(i.kind, i.value) for i in found if kind is None or i.kind == kind]


def compare(before, after, **kwargs):
    findings, warnings = check_fidelity.compare(
        textwrap.dedent(before), textwrap.dedent(after), **kwargs
    )
    return [(f.change, f.kind, f.value) for f in findings], warnings


ORIGINAL = """\
    # Sync settings

    The agent copies files every 15 min. Set `--interval=15m` or `SYNCD_INTERVAL`; the
    environment variable wins. Values below 60 s are rejected. See [Conflicts](../guide/conflicts.md).

    ![Sync loop from scan to upload](img/sync-loop.png)

    > **Warning:** `SYNCD_DELETE=mirror` deletes remote files that are gone locally.

    | Setting | Default |
    |---|---|
    | `--interval` | 15m |
    | `--threads` | 4 |

    ```sh
    syncd run --interval=15m
    ```
    """


class ExtractTest(unittest.TestCase):
    def test_inline_code_spans(self):
        self.assertEqual(items("Run `syncd run` then `syncd status`.\n", "code"),
                         [("code", "syncd run"), ("code", "syncd status")])

    def test_double_backtick_span(self):
        self.assertEqual(items("Use ``a `b` c`` here.\n", "code"), [("code", "a `b` c")])

    def test_fenced_block_is_whitespace_normalized(self):
        self.assertEqual(items("```sh\nsyncd   run\n  --x\n```\n", "block"), [("block", "syncd run --x")])

    def test_code_inside_fence_is_not_an_inline_span(self):
        self.assertEqual(items("```\nuse `x` here\n```\n", "code"), [])

    def test_tilde_fence(self):
        self.assertEqual(items("~~~\nmake\n~~~\n", "block"), [("block", "make")])

    def test_link_targets(self):
        self.assertEqual(items("See [A](../a.md#top) and [B](https://example.com).\n", "link"),
                         [("link", "../a.md#top"), ("link", "https://example.com")])

    def test_link_with_title(self):
        self.assertEqual(items('See [A](a.md "The A page").\n', "link"), [("link", "a.md")])

    def test_reference_definition(self):
        self.assertEqual(items("[ref]: ../b.md\n", "link"), [("link", "../b.md")])

    def test_autolink(self):
        self.assertEqual(items("Go to <https://example.org/x>.\n", "link"), [("link", "https://example.org/x")])

    def test_image_target_and_caption(self):
        got = items("![Retry flow](img/r.png)\n")
        self.assertIn(("image", "img/r.png"), got)
        self.assertIn(("caption", "Retry flow"), got)
        self.assertNotIn(("link", "img/r.png"), got)

    def test_env_var_in_prose(self):
        self.assertEqual(items("Set SYNCD_TOKEN before start.\n", "env"), [("env", "SYNCD_TOKEN")])

    def test_env_var_inside_code_is_counted_once_as_code(self):
        got = items("Set `SYNCD_TOKEN` before start.\n")
        self.assertIn(("code", "SYNCD_TOKEN"), got)
        self.assertNotIn(("env", "SYNCD_TOKEN"), got)

    def test_numbers_with_units_normalized(self):
        self.assertEqual(items("Every 15 min, at most 2,5 GiB or 60s.\n", "number"),
                         [("number", "15min"), ("number", "2.5GiB"), ("number", "60s")])

    def test_list_markers_are_not_numbers(self):
        self.assertEqual(items("1. Install it.\n2. Run it.\n", "number"), [])

    def test_admonitions(self):
        got = items("> **Warning:** careful.\n\n> [!NOTE]\n> text\n\n!!! danger \"x\"\n", "admonition")
        self.assertEqual(got, [("admonition", "callout"), ("admonition", "note"), ("admonition", "danger")])

    def test_table_cells_and_shape(self):
        got = items("| A | B |\n|---|---|\n| `x` | 4 |\n| manual | Number of workers |\n")
        self.assertIn(("table", "2 cols"), got)
        self.assertIn(("code", "x"), got)
        self.assertIn(("number", "4"), got)
        self.assertIn(("cell", "manual"), got)
        self.assertNotIn(("cell", "Number of workers"), got)
        self.assertEqual([v for k, v in got if k == "row"], ["2 rows"])

    def test_one_dash_rule_and_no_outer_pipes(self):
        got = items("A | B\n-|-\nx | 1\ny | 2\n")
        self.assertIn(("table", "2 cols"), got)
        self.assertIn(("row", "2 rows"), got)
        self.assertIn(("cell", "y"), got)

    def test_heading_anchor(self):
        self.assertEqual(items("## Retry & back-off\n", "anchor"), [("anchor", "retry--back-off")])

    def test_front_matter_keys_and_values(self):
        got = items("---\ntitle: Getting started\ntimeout: 30s\n---\n# X\n")
        self.assertIn(("key", "title"), got)
        self.assertIn(("number", "30s"), got)
        self.assertNotIn(("block", "title: Getting started"), got)

    def test_line_numbers(self):
        found = check_fidelity.extract("intro\n\nrun `a`\n")
        self.assertEqual([(i.kind, i.line) for i in found if i.kind == "code"], [("code", 3)])


class MarkdownEdgeTest(unittest.TestCase):
    def test_wrapped_code_span(self):
        got = items("Run `syncd run --log-level\ndebug` and set `--threads` first.\n", "code")
        self.assertEqual(got, [("code", "syncd run --log-level debug"), ("code", "--threads")])

    def test_wrapped_link_text(self):
        self.assertEqual(items("See [the sync\nguide](guide/sync.md) now.\n", "link"), [("link", "guide/sync.md")])

    def test_wrapped_item_has_line_of_its_start(self):
        found = check_fidelity.extract("intro\n\nSee `a\nb` and\n`c`.\n")
        self.assertEqual([(i.value, i.line) for i in found if i.kind == "code"], [("a b", 3), ("c", 5)])

    def test_link_text_with_brackets(self):
        self.assertEqual(items("See [RFC [7231]](https://ietf.org/rfc7231).\n", "link"),
                         [("link", "https://ietf.org/rfc7231")])

    def test_fence_indented_in_list_item(self):
        got = items("- Install:\n\n    ```sh\n    syncd run --force\n    ```\n", "block")
        self.assertEqual(got, [("block", "syncd run --force")])

    def test_one_line_triple_backtick_span_is_not_a_fence(self):
        got = items("```make all``` builds everything.\n\nThen set `--force`.\n")
        self.assertIn(("code", "make all"), got)
        self.assertIn(("code", "--force"), got)
        self.assertNotIn("block", [k for k, _ in got])

    def test_html_comments_are_ignored(self):
        self.assertEqual(items("<!-- TODO: 3 retries\nlater -->\nText.\n"), [])

    def test_html_comment_keeps_line_numbers(self):
        found = check_fidelity.extract("<!-- a\nb -->\nrun `x`\n")
        self.assertEqual([(i.value, i.line) for i in found if i.kind == "code"], [("x", 3)])

    def test_numbers_in_headings(self):
        self.assertIn(("number", "30s"), items("## Retry after 30 s\n"))


class CompareTest(unittest.TestCase):
    def test_reflowed_paragraph_passes(self):
        before = "Run `syncd run --log-level\ndebug` and see [the sync\nguide](guide/sync.md).\n"
        after = "Run `syncd run --log-level debug` and see [the sync guide](guide/sync.md).\n"
        self.assertEqual(compare(before, after)[0], [])

    def test_table_to_list_passes(self):
        before = "| Flag | Default |\n|---|---|\n| `--timeout` | 500 ms |\n| `--size` | 1,000 |\n"
        after = "- `--timeout` defaults to 500 ms.\n- `--size` defaults to 1,000.\n"
        findings = compare(before, after)[0]
        self.assertEqual([f for f in findings if f[1] not in ("table", "row")], [])

    def test_translated_table_cells_pass(self):
        before = "| Flag | Meaning |\n|---|---|\n| `--threads` | Number of workers |\n| `--guide` | [Guide](a.md) |\n"
        after = "| Flag | Significato |\n|---|---|\n| `--threads` | Numero di worker |\n| `--guide` | [Guida](a.md) |\n"
        self.assertEqual(compare(before, after)[0], [])

    def test_decimal_comma_in_cell_matches_prose(self):
        before = "Timeout is 1.5 s.\n"
        after = "| Timeout |\n|---|\n| 1,5 s |\n"
        findings = compare(before, after)[0]
        self.assertEqual([f for f in findings if f[1] not in ("table", "row")], [])

    def test_translated_callout_label_passes(self):
        self.assertEqual(compare("> **Note:** run `make` first.\n", "> **Nota:** esegui prima `make`.\n")[0], [])

    def test_translated_front_matter_title_passes(self):
        self.assertEqual(compare("---\ntitle: Getting started\n---\n", "---\ntitle: Per iniziare\n---\n")[0], [])

    def test_dropped_command_in_indented_fence_fails(self):
        before = "- Install:\n\n    ```sh\n    syncd run --force\n    ```\n"
        after = "- Install:\n\n    ```sh\n    syncd run\n    ```\n"
        self.assertEqual(sorted(compare(before, after)[0]),
                         [("added", "block", "syncd run"), ("missing", "block", "syncd run --force")])

    def test_identical_text_passes(self):
        self.assertEqual(compare(ORIGINAL, ORIGINAL), ([], []))

    def test_rewritten_prose_and_reordered_sections_pass(self):
        after = """\
            # Sync settings

            > **Warning:** `SYNCD_DELETE=mirror` deletes remote files that are gone locally.

            | Setting | Default |
            |---|---|
            | `--interval` | 15m |
            | `--threads` | 4 |

            The agent syncs every 15 min.

            - Set it with `--interval=15m` or with `SYNCD_INTERVAL`.
            - If both are set, the environment variable wins.
            - Anything under 60 s is refused.

            Conflicts are covered in [Conflicts](../guide/conflicts.md).

            ```sh
            syncd run   --interval=15m
            ```

            ![Sync loop from scan to upload](img/sync-loop.png)
            """
        self.assertEqual(compare(ORIGINAL, after), ([], []))

    def test_translation_keeps_code_passes(self):
        after = ORIGINAL.replace("The agent copies files every", "L'agente copia i file ogni") \
                        .replace("Values below", "Valori sotto")
        self.assertEqual(compare(ORIGINAL, after)[0], [])

    def test_dropped_env_var_fails(self):
        after = ORIGINAL.replace("Set `--interval=15m` or `SYNCD_INTERVAL`", "Set `--interval=15m`")
        self.assertEqual(compare(ORIGINAL, after)[0], [("missing", "code", "SYNCD_INTERVAL")])

    def test_value_still_present_in_another_form_passes(self):
        before = "Run `syncd status` to check. Threads default to 4.\n\n| Setting | Default |\n|---|---|\n| threads | 4 |\n"
        after = "To check:\n\n```sh\nsyncd status\n```\n\n| Setting | Default |\n|---|---|\n| threads | 4 |\n"
        self.assertEqual(compare(before, after)[0], [])

    def test_number_is_not_found_inside_a_longer_number(self):
        before = "At most 32 messages.\n"
        after = "At most 320 messages.\n"
        self.assertEqual(sorted(compare(before, after)[0]),
                         [("added", "number", "320"), ("missing", "number", "32")])

    def test_changed_default_fails_both_ways(self):
        after = ORIGINAL.replace("| `--threads` | 4 |", "| `--threads` | 8 |")
        self.assertEqual(sorted(compare(ORIGINAL, after)[0]),
                         [("added", "number", "8"), ("missing", "number", "4")])

    def test_changed_relative_link_fails(self):
        after = ORIGINAL.replace("../guide/conflicts.md", "guide/conflicts.md")
        self.assertEqual(sorted(compare(ORIGINAL, after)[0]),
                         [("added", "link", "guide/conflicts.md"), ("missing", "link", "../guide/conflicts.md")])

    def test_repeated_value_dropped_once_passes_by_default(self):
        before = "Run `make` first. Later run `make` again.\n"
        after = "Run `make` first.\n"
        self.assertEqual(compare(before, after)[0], [])

    def test_strict_count_reports_one_of_two_occurrences_dropped(self):
        before = "Run `make` first. Later run `make` again.\n"
        after = "Run `make` first.\n"
        self.assertEqual(compare(before, after, strict=True)[0], [("missing", "code", "make")])

    def test_admonitions_are_counted_even_by_default(self):
        before = "> **Warning:** a\n\n> **Warning:** b\n"
        after = "> **Warning:** a and b\n"
        self.assertEqual(compare(before, after)[0], [("missing", "admonition", "callout")])

    def test_dropped_warning_fails(self):
        after = ORIGINAL.replace("> **Warning:** `SYNCD_DELETE=mirror`", "`SYNCD_DELETE=mirror`")
        self.assertEqual(compare(ORIGINAL, after)[0], [("missing", "admonition", "callout")])

    def test_dropped_limit_fails(self):
        after = ORIGINAL.replace(" Values below 60 s are rejected.", "")
        self.assertEqual(compare(ORIGINAL, after)[0], [("missing", "number", "60s")])

    def test_allow_suppresses_matching_values(self):
        after = ORIGINAL.replace(" Values below 60 s are rejected.", "")
        self.assertEqual(compare(ORIGINAL, after, allow=[r"^60s$"])[0], [])

    def test_anchor_change_is_a_warning_by_default(self):
        after = ORIGINAL.replace("# Sync settings", "# Synchronization settings")
        findings, warnings = compare(ORIGINAL, after)
        self.assertEqual(findings, [])
        self.assertEqual(len(warnings), 2)
        self.assertTrue(all("anchor" in w for w in warnings))

    def test_anchor_change_is_a_finding_when_asked(self):
        after = ORIGINAL.replace("# Sync settings", "# Synchronization settings")
        findings, _ = compare(ORIGINAL, after, anchors="error")
        self.assertEqual(sorted(findings), [("added", "anchor", "synchronization-settings"),
                                            ("missing", "anchor", "sync-settings")])

    def test_anchors_off(self):
        after = ORIGINAL.replace("# Sync settings", "# Synchronization settings")
        self.assertEqual(compare(ORIGINAL, after, anchors="off"), ([], []))


class MainTest(unittest.TestCase):
    def run_main(self, before, after, *extra):
        with tempfile.TemporaryDirectory() as tmp:
            b, a = Path(tmp, "before.md"), Path(tmp, "after.md")
            b.write_text(textwrap.dedent(before), encoding="utf-8")
            a.write_text(textwrap.dedent(after), encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = check_fidelity.main([str(b), str(a), *extra])
            return code, out.getvalue(), err.getvalue()

    def test_exit_0_when_nothing_lost(self):
        code, out, _ = self.run_main(ORIGINAL, ORIGINAL)
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_exit_1_and_location_when_something_lost(self):
        after = ORIGINAL.replace(" Values below 60 s are rejected.", "")
        code, out, _ = self.run_main(ORIGINAL, after)
        self.assertEqual(code, 1)
        self.assertRegex(out, r"before\.md:4: missing number: 60s")

    def test_added_item_reports_after_location(self):
        after = ORIGINAL + "\nAlso run `syncd doctor`.\n"
        code, out, _ = self.run_main(ORIGINAL, after)
        self.assertEqual(code, 1)
        self.assertRegex(out, r"after\.md:\d+: added code: syncd doctor")

    def test_exit_2_on_missing_file(self):
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            code = check_fidelity.main(["/nonexistent/a.md", "/nonexistent/b.md"])
        self.assertEqual(code, 2)
        self.assertIn("cannot read", err.getvalue())

    def test_exit_2_on_bad_allow_regex(self):
        code, _, err = self.run_main(ORIGINAL, ORIGINAL, "--allow", "(")
        self.assertEqual(code, 2)
        self.assertIn("--allow", err)

    def test_strict_count_flag(self):
        before = "Run `make` first. Later run `make` again.\n"
        code, out, _ = self.run_main(before, "Run `make` first.\n", "--strict-count")
        self.assertEqual(code, 1)
        self.assertIn("missing code: make", out)

    def test_anchor_warning_goes_to_stderr_with_exit_0(self):
        after = ORIGINAL.replace("# Sync settings", "# Synchronization settings")
        code, out, err = self.run_main(ORIGINAL, after)
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("anchor", err)


if __name__ == "__main__":
    unittest.main()

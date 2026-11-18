"""Tests for skills/technical-writing/scripts/scan_leaks.py."""

import io
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "technical-writing" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import scan_leaks  # noqa: E402


def scan(name, source, **kwargs):
    """Scan an in-memory file and return (line, match, rule) tuples."""
    rules = scan_leaks.build_rules(kwargs.get("patterns", []))
    allow = scan_leaks.build_allowlist(kwargs.get("allow", []))
    whole = kwargs.get("whole", False)
    findings = scan_leaks.scan_text(name, textwrap.dedent(source), rules, allow, whole=whole)
    return [(f.line, f.match, f.rule) for f in findings]


def matches(name, source, **kwargs):
    return [m for _, m, _ in scan(name, source, **kwargs)]


class GoTest(unittest.TestCase):
    def test_doc_comment_of_exported_func_is_public(self):
        src = """\
            package orders

            // Cancel cancels the order (FR-112).
            func Cancel(o *Order) error {
            \t// FR-112: only pending or confirmed orders can be cancelled.
            \treturn nil
            }
            """
        self.assertEqual(scan("orders.go", src), [(3, "FR-112", "requirement-id")])

    def test_comment_separated_by_blank_line_is_not_doc(self):
        src = """\
            package orders

            // FR-112 lives here.

            func Cancel(o *Order) error { return nil }
            """
        self.assertEqual(scan("orders.go", src), [])

    def test_unexported_func_comment_is_internal(self):
        src = """\
            package orders

            // cancel implements FR-112.
            func cancel(o *order) error { return nil }
            """
        self.assertEqual(scan("orders.go", src), [])

    def test_method_type_var_const_and_fields(self):
        src = """\
            package orders

            // Order is an order (US-1).
            type Order struct {
            \t// ID identifies the order, see PAY-12.
            \tID string
            \t// internal field note PAY-13
            \tstate string
            }

            // Close closes it (FR-2).
            func (o *Order) Close() {}

            // ErrX is returned per FR-3.
            var ErrX = errors.New("x")

            const (
            \t// Pending is the first state (FR-4).
            \tPending State = "PENDING"
            )
            """
        self.assertEqual(
            matches("orders.go", src), ["US-1", "PAY-12", "FR-2", "FR-3", "FR-4"]
        )

    def test_package_doc_comment(self):
        src = """\
            // Package orders implements FR-1.
            package orders
            """
        self.assertEqual(matches("doc.go", src), ["FR-1"])


class CSharpTest(unittest.TestCase):
    def test_triple_slash_public_double_slash_internal(self):
        src = """\
            /// <summary>Lists orders (DEM-ORD-004).</summary>
            // DEM-ORD-004, AD-7: paginated.
            public static class ListOrders {}
            """
        self.assertEqual(scan("A.cs", src), [(1, "ORD-004", "tracker-key")])

    def test_multiline_with_description_is_public(self):
        src = """\
            app.MapGet("/v1/orders", Handler)
               .WithSummary("List orders")
               .WithDescription(
                   "Newest first. " +
                   "Page size is provisional (OQ-12).");
            var x = 1; // OQ-13 stays internal
            """
        self.assertEqual(scan("A.cs", src), [(5, "OQ-12", "requirement-id")])


class JavaScriptFamilyTest(unittest.TestCase):
    def test_jsdoc_block_with_continuation_lines(self):
        src = """\
            /**
             * Creates an order.
             * Implements FR-9.
             */
            export function create() {
              // FR-9: validation first
              /* FR-10 block comment */
            }
            """
        self.assertEqual(scan("a.ts", src), [(3, "FR-9", "requirement-id")])

    def test_single_line_jsdoc(self):
        self.assertEqual(matches("A.java", "/** See FR-9. */\nclass A {}\n"), ["FR-9"])

    def test_java_annotation_metadata(self):
        src = '@Operation(summary = "Create order (FR-5)")\npublic void create() {}\n'
        self.assertEqual(matches("A.java", src), ["FR-5"])


class PythonTest(unittest.TestCase):
    def test_public_docstrings_are_public_hash_comments_are_not(self):
        src = '''\
            """Billing module (FR-1)."""


            def download(invoice_id):
                """Download an invoice as a PDF (BFR-7)."""
                # BFR-7: tenants never see each other's invoices
                return None


            class Client:
                """Client.

                Timeout per NFR-3.
                """

                def _private(self):
                    """Helper for FR-99."""

                def __init__(self):
                    """Create (FR-100)."""
            '''
        self.assertEqual(
            scan("m.py", src),
            [
                (1, "FR-1", "requirement-id"),
                (5, "BFR-7", "requirement-id"),
                (13, "NFR-3", "requirement-id"),
                (20, "FR-100", "requirement-id"),
            ],
        )

    def test_fastapi_description_keyword(self):
        src = """\
            @app.get(
                "/x",
                summary="Get x",
                description=(
                    "Returns x. "
                    "See BFR-8."
                ),
            )
            def get_x():
                pass
            """
        self.assertEqual(scan("m.py", src), [(6, "BFR-8", "requirement-id")])

    def test_syntax_error_falls_back_to_metadata_only(self):
        src = 'def broken(:\n    """FR-1"""\nx = dict(description="FR-2")\n'
        self.assertEqual(matches("m.py", src), ["FR-2"])


class RustTest(unittest.TestCase):
    def test_outer_and_inner_doc_comments(self):
        src = "//! Crate docs (FR-1).\n/// Fn docs (FR-2).\n// FR-3 internal\nfn a() {}\n"
        self.assertEqual(matches("lib.rs", src), ["FR-1", "FR-2"])


class WholeFileTest(unittest.TestCase):
    def test_openapi_yaml_is_scanned_whole_including_comments(self):
        src = """\
            # Contract for DEM-INT.1, see ADR 0019
            openapi: 3.1.0
            info:
              title: Orders
            x-requirements: [FR-1]
            """
        self.assertEqual(matches("orders.yaml", src), ["ADR 0019", "FR-1"])

    def test_non_openapi_yaml_is_not_scanned(self):
        self.assertEqual(matches("ci.yaml", "steps:\n  - run: echo FR-1\n"), [])

    def test_openapi_json_and_asyncapi(self):
        self.assertEqual(matches("a.json", '{"openapi": "3.1.0", "x": "FR-1"}'), ["FR-1"])
        self.assertEqual(matches("e.yml", "asyncapi: 3.0.0\nx: FR-2\n"), ["FR-2"])

    def test_graphql_is_whole(self):
        self.assertEqual(matches("s.graphql", '"""Order (FR-1)"""\ntype Order { id: ID }\n'), ["FR-1"])

    def test_explicit_whole_markdown(self):
        src = "# Guide\n\nRe-run with kubectl on redis-wh-01.internal (PAY-1432).\nTODO: finish\n"
        self.assertEqual(
            scan("guide.md", src, whole=True),
            [
                (3, "redis-wh-01.internal", "internal-host"),
                (3, "PAY-1432", "tracker-key"),
                (4, "TODO", "work-marker"),
            ],
        )

    def test_markdown_not_scanned_unless_whole(self):
        self.assertEqual(matches("README.md", "See FR-1.\n"), [])

    def test_unknown_extension_is_skipped(self):
        self.assertEqual(matches("data.bin", "FR-1"), [])


class RulesTest(unittest.TestCase):
    def whole(self, text, **kwargs):
        return matches("x.md", text, whole=True, **kwargs)

    def test_standard_names_are_allowlisted(self):
        text = "SHA-256, UTF-8, ISO-8601, RFC-9457, CVE-2024-1234, AES-256, HMAC-SHA256"
        self.assertEqual(self.whole(text), [])

    def test_issue_reference(self):
        self.assertEqual(self.whole("Fixed, closes #872."), ["#872"])

    def test_private_ips(self):
        text = "10.1.2.3 172.20.0.1 192.168.1.10 8.8.8.8 172.32.0.1"
        self.assertEqual(self.whole(text), ["10.1.2.3", "172.20.0.1", "192.168.1.10"])

    def test_project_pattern_and_allow(self):
        text = "Codename Falcon handles DEM-INT.1; EU-27 is fine."
        found = self.whole(text, patterns=[r"codename=\bFalcon\b", r"DEM-[A-Z]+\.\d+"], allow=[r"EU-27"])
        self.assertEqual(found, ["Falcon", "DEM-INT.1"])

    def test_overlapping_matches_reported_once(self):
        self.assertEqual(self.whole("Story ABC-12"), ["ABC-12"])

    def test_bad_pattern_raises_value_error(self):
        with self.assertRaises(ValueError):
            scan_leaks.build_rules(["("])


class CliTest(unittest.TestCase):
    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = scan_leaks.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_findings_exit_1_and_clean_exit_0(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d, "a.go")
            bad.write_text("package a\n\n// F does FR-1.\nfunc F() {}\n")
            good = Path(d, "b.go")
            good.write_text("package a\n\n// G does nothing.\nfunc G() {}\n")
            code, out, _ = self.run_main(str(bad), str(good))
            self.assertEqual(code, 1)
            self.assertEqual(out.strip(), f"{bad}:3: FR-1 [requirement-id]")
            code, out, _ = self.run_main(str(good))
            self.assertEqual((code, out), (0, ""))

    def test_whole_glob(self):
        with tempfile.TemporaryDirectory() as d:
            doc = Path(d, "docs", "guide.md")
            doc.parent.mkdir()
            doc.write_text("See FR-1.\n")
            code, out, _ = self.run_main("--whole", "*/docs/*.md", str(doc))
            self.assertEqual(code, 1)
            self.assertIn("FR-1", out)

    def test_files_may_follow_options(self):
        with tempfile.TemporaryDirectory() as d:
            code_file = Path(d, "a.go")
            code_file.write_text("package a\n\n// F does FR-1.\nfunc F() {}\n")
            doc = Path(d, "notes.md")
            doc.write_text("Fixes PAY-7.\n")
            code, out, _ = self.run_main(str(code_file), "--whole", "*.md", str(doc))
            self.assertEqual(code, 1)
            self.assertIn("FR-1", out)
            self.assertIn("PAY-7", out)

    def test_missing_file_exit_2(self):
        code, _, err = self.run_main("/nonexistent/x.go")
        self.assertEqual(code, 2)
        self.assertIn("/nonexistent/x.go", err)

    def test_bad_pattern_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d, "a.go")
            f.write_text("package a\n")
            code, _, err = self.run_main("--pattern", "(", str(f))
            self.assertEqual(code, 2)
            self.assertIn("pattern", err)

    def test_no_files_exit_2(self):
        code, _, err = self.run_main()
        self.assertEqual(code, 2)

    def test_git_diff_scans_changed_and_untracked_files(self):
        with tempfile.TemporaryDirectory() as d:
            git = ["git", "-C", d, "-c", "user.name=t", "-c", "user.email=t@example.com"]
            subprocess.run(git + ["init", "-q", "-b", "main"], check=True)
            Path(d, "old.go").write_text("package a\n\n// Old is FR-0.\nfunc Old() {}\n")
            subprocess.run(git + ["add", "."], check=True)
            subprocess.run(git + ["commit", "-q", "-m", "init"], check=True)
            Path(d, "new.go").write_text("package a\n\n// New is FR-1.\nfunc New() {}\n")
            cwd = os.getcwd()
            try:
                os.chdir(d)
                code, out, _ = self.run_main("--git-diff", "main")
            finally:
                os.chdir(cwd)
            self.assertEqual(code, 1)
            self.assertIn("new.go:3: FR-1", out)
            self.assertNotIn("FR-0", out)

    def test_git_diff_outside_repo_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            cwd = os.getcwd()
            try:
                os.chdir(d)
                code, _, err = self.run_main("--git-diff", "main")
            finally:
                os.chdir(cwd)
            self.assertEqual(code, 2)
            self.assertIn("git", err)

    def test_script_runs_as_program(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "scan_leaks.py"), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--whole", result.stdout)


if __name__ == "__main__":
    unittest.main()

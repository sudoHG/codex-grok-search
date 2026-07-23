import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "codex-grok-search" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_search  # noqa: E402


@contextmanager
def fake_environment(_run_dir):
    yield {"PATH": os.environ.get("PATH", "")}


class RunSearchTests(unittest.TestCase):
    def make_args(self, **overrides):
        values = {
            "query": "Find the latest posts",
            "platform": "x",
            "depth": "quick",
            "since": None,
            "until": None,
            "retention_days": 7,
            "max_turns": 40,
            "timeout": 30,
            "keep_run": False,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_prompt_guides_without_enforcing_platform_or_schema(self):
        now = datetime(2026, 7, 23, tzinfo=timezone.utc)
        prompt = run_search.build_prompt(
            "Find ten posts", "x", now - timedelta(days=7), now, "quick"
        )
        self.assertIn("Use X Search first", prompt)
        self.assertIn("include useful public-web context", prompt)
        self.assertIn("Return a useful answer in Markdown", prompt)
        self.assertNotIn("Required JSON schema", prompt)
        self.assertNotIn("additional fields are forbidden", prompt)

    def test_extract_answer_accepts_unfiltered_grok_output(self):
        answer = (
            "X post: http://x.com/example/status/1\n\n"
            "Context: https://example.com/report"
        )
        envelope = json.dumps({"sessionId": "anything", "text": answer})
        extracted, source = run_search.extract_answer(envelope)
        self.assertEqual(extracted, answer)
        self.assertEqual(source, "grok_json")

        raw, raw_source = run_search.extract_answer(answer)
        self.assertEqual(raw, answer)
        self.assertEqual(raw_source, "raw_stdout")
        empty, empty_source = run_search.extract_answer('{"text":""}')
        self.assertIsNone(empty)
        self.assertEqual(empty_source, "grok_json_without_text")

    def test_no_content_validation_or_reddit_refetch_remains(self):
        self.assertFalse(hasattr(run_search, "validate_result_payload"))
        self.assertFalse(hasattr(run_search, "repair_out_of_window_payload"))
        self.assertFalse(hasattr(run_search, "verify_reddit_urls"))
        self.assertFalse(hasattr(run_search, "inspect_isolation"))
        self.assertFalse(hasattr(run_search, "check_grok_auth"))
        source = Path(run_search.__file__).read_text(encoding="utf-8")
        self.assertNotIn("finding_platform_out_of_scope", source)
        self.assertNotIn("invalid_direct_url", source)
        self.assertNotIn("grok models", source)
        self.assertNotIn("grok inspect", source)

    def test_run_delivers_mixed_platform_and_http_result_verbatim(self):
        answer = (
            "# Results\n\n"
            "- X: http://x.com/example/status/1\n"
            "- Web context: https://example.com/context\n"
            "- Date: unable to verify"
        )
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "runs"
            captured = {}

            def fake_process(command, cwd, env, timeout):
                captured["command"] = command
                captured["cwd"] = cwd
                return 0, json.dumps({"text": answer}), "", False

            with patch("run_search.default_cache_root", return_value=cache), patch(
                "run_search.find_grok", return_value="/fake/grok"
            ), patch("run_search.isolated_environment", fake_environment), patch(
                "run_search.run_process", side_effect=fake_process
            ), redirect_stdout(io.StringIO()) as output:
                self.assertEqual(run_search.run_grok(self.make_args()), 0)

            status = json.loads(output.getvalue())
            self.assertTrue(status["ok"])
            self.assertEqual(
                Path(status["result_path"]).read_text(encoding="utf-8"),
                answer + "\n",
            )
            self.assertEqual(captured["cwd"], Path(status["result_path"]).parent)
            command = captured["command"]
            self.assertNotIn("--sandbox", command)
            self.assertNotIn("inspect", command)
            self.assertEqual(
                command[command.index("--tools") + 1],
                "x_search,web_search,web_fetch",
            )

    def test_nonzero_exit_with_answer_is_still_delivered_as_partial(self):
        with tempfile.TemporaryDirectory() as tmp, patch(
            "run_search.default_cache_root", return_value=Path(tmp) / "runs"
        ), patch("run_search.find_grok", return_value="/fake/grok"), patch(
            "run_search.isolated_environment", fake_environment
        ), patch(
            "run_search.run_process",
            return_value=(1, "Useful answer with http://example.com", "late error", False),
        ), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(run_search.run_grok(self.make_args()), 0)
        status = json.loads(output.getvalue())
        self.assertTrue(status["ok"])
        self.assertEqual(status["status"], "partial")
        self.assertIn("warning", status)

    def test_auth_is_reported_only_after_real_run_returns_no_answer(self):
        with tempfile.TemporaryDirectory() as tmp, patch(
            "run_search.default_cache_root", return_value=Path(tmp) / "runs"
        ), patch("run_search.find_grok", return_value="/fake/grok"), patch(
            "run_search.isolated_environment", fake_environment
        ), patch(
            "run_search.run_process",
            side_effect=[
                (1, "", "token expired; re-authentication required", False),
                (1, "", "export failed", False),
            ],
        ), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(run_search.run_grok(self.make_args()), 1)
        status = json.loads(output.getvalue())
        self.assertEqual(status["error"], "grok_not_authenticated")

    def test_isolated_environment_exposes_no_unrelated_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            grok_home = home / ".grok"
            grok_home.mkdir()
            (grok_home / "auth.json").write_text('{"token":"old"}', encoding="utf-8")
            run_dir = home / "cache" / "run"
            run_dir.mkdir(parents=True)
            with patch("run_search.Path.home", return_value=home), patch.dict(
                os.environ,
                {"SECRET_FOR_TEST": "do-not-copy", "XAI_API_KEY": "do-not-copy"},
                clear=False,
            ):
                with run_search.isolated_environment(run_dir) as env:
                    self.assertNotIn("SECRET_FOR_TEST", env)
                    self.assertNotIn("XAI_API_KEY", env)
                    self.assertNotEqual(Path(env["HOME"]), home)
                    isolated_grok_home = Path(env["GROK_HOME"])
                    self.assertEqual(
                        json.loads((isolated_grok_home / "auth.json").read_text()),
                        {"token": "old"},
                    )
                    config = (isolated_grok_home / "config.toml").read_text()
                    self.assertIn("skills = false", config)
                    (isolated_grok_home / "auth.json").write_text(
                        '{"token":"refreshed"}', encoding="utf-8"
                    )
            self.assertEqual(
                json.loads((grok_home / "auth.json").read_text()),
                {"token": "refreshed"},
            )

    def test_cleanup_removes_only_expired_unpinned_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_time = datetime.now(timezone.utc) - timedelta(days=8)
            old_id, old = run_search.create_run(
                root, old_time, False
            )
            keep_id, keep = run_search.create_run(
                root, old_time, True
            )
            for run_id, run_dir in ((old_id, old), (keep_id, keep)):
                run_search.write_json(
                    run_dir / "manifest.json",
                    {
                        "run_id": run_id,
                        "created_at": run_search.iso_utc(old_time),
                    },
                )
            removed = run_search.cleanup_expired(root, 7)
            self.assertEqual(removed, [old_id])
            self.assertFalse(old.exists())
            self.assertTrue(keep.exists())

    def test_cli_has_no_content_or_version_gate_options(self):
        parser = run_search.build_parser()
        args = parser.parse_args(["run", "query", "--platform", "reddit"])
        self.assertEqual(args.platform, "reddit")
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["run", "query", "--model", "other"])
            with self.assertRaises(SystemExit):
                parser.parse_args(["run", "query", "--max-runs", "1"])


if __name__ == "__main__":
    unittest.main()

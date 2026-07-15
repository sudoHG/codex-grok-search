import sys
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "codex-grok-search" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from reddit_dates import (  # noqa: E402
    RejectRedirects,
    extract_reddit_urls,
    fetch_old_reddit,
    old_reddit_url,
    parse_submission_datetime,
    verify_reddit_urls,
    verify_reddit_url,
)


class RedditDatesTests(unittest.TestCase):
    def test_extracts_and_deduplicates_submission_urls(self):
        text = """
        First https://www.reddit.com/r/codex/comments/abc123/example/.
        Again https://www.reddit.com/r/codex/comments/abc123/example/
        Short https://redd.it/def456
        No subreddit https://www.reddit.com/comments/ghi789/example/
        """
        self.assertEqual(
            extract_reddit_urls(text),
            [
                "https://www.reddit.com/r/codex/comments/abc123/example/",
                "https://redd.it/def456",
                "https://www.reddit.com/comments/ghi789/example/",
            ],
        )

    def test_normalizes_old_reddit_url(self):
        self.assertEqual(
            old_reddit_url("https://www.reddit.com/r/codex/comments/abc123/example/"),
            "https://old.reddit.com/r/codex/comments/abc123/example/",
        )
        self.assertEqual(
            old_reddit_url("https://redd.it/abc123"),
            "https://old.reddit.com/comments/abc123/",
        )

    def test_parses_target_submission_time_not_comment_time(self):
        html = """
        <div class="thing" data-fullname="t3_abc123" data-timestamp="1782214440000">
          <time datetime="2026-06-23T11:34:00+00:00">22 days ago</time>
          <div class="comment" data-fullname="t1_comment">
            <time datetime="2026-07-15T01:00:00+00:00">now</time>
          </div>
        </div>
        """
        self.assertEqual(
            parse_submission_datetime(html, "abc123"),
            "2026-06-23T11:34:00Z",
        )

    def test_does_not_accept_nested_comment_time_before_submission_time(self):
        html = """
        <div class="thing" data-fullname="t3_abc123">
          <div class="comment" data-fullname="t1_comment">
            <time datetime="2026-07-15T01:00:00+00:00">now</time>
          </div>
          <time datetime="2026-06-23T11:34:00+00:00">22 days ago</time>
        </div>
        """
        self.assertEqual(
            parse_submission_datetime(html, "abc123"),
            "2026-06-23T11:34:00Z",
        )

    def test_extraction_and_verification_are_bounded(self):
        text = "\n".join(
            f"https://redd.it/post{index}" for index in range(30)
        )
        self.assertEqual(len(extract_reddit_urls(text)), 30)
        results = verify_reddit_urls(
            ["https://redd.it/one", "https://redd.it/two"],
            fetcher=lambda _: "<html></html>",
            total_budget=0,
        )
        self.assertEqual(len(results), 2)
        self.assertTrue(
            all(item["error"] == "verification_budget_exhausted" for item in results)
        )

        started = time.monotonic()
        slow = verify_reddit_urls(
            ["https://redd.it/slow"],
            fetcher=lambda _: (time.sleep(0.2) or "<html></html>"),
            total_budget=0.02,
        )
        self.assertLess(time.monotonic() - started, 0.1)
        self.assertEqual(slow[0]["error"], "verification_budget_exhausted")

        many = [f"https://redd.it/post{index}" for index in range(25)]
        calls = []
        bounded = verify_reddit_urls(
            many,
            fetcher=lambda url: (calls.append(url) or "<html></html>"),
        )
        self.assertEqual(len(bounded), 25)
        self.assertEqual(len(calls), 20)
        self.assertTrue(
            all(item["error"] == "verification_limit_exceeded" for item in bounded[20:])
        )

    def test_fetch_rejects_oversized_response(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def geturl(self):
                return "https://old.reddit.com/comments/abc123/"

            def read(self, _):
                return b"x" * (2 * 1024 * 1024 + 1)

        with patch("reddit_dates._open_without_redirects", return_value=FakeResponse()):
            with self.assertRaises(ValueError):
                fetch_old_reddit("https://old.reddit.com/comments/abc123/")

    def test_fetch_rejects_redirect_away_from_exact_old_reddit_submission(self):
        class FakeResponse:
            def __init__(self, final_url):
                self.final_url = final_url

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def geturl(self):
                return self.final_url

            def read(self, _):
                return b'<div data-fullname="t3_abc123" data-timestamp="1"></div>'

        unsafe = (
            "http://127.0.0.1/internal",
            "https://old.reddit.com/comments/different/",
            "https://old.reddit.com:444/comments/abc123/",
        )
        for final_url in unsafe:
            with self.subTest(final_url=final_url), patch(
                "reddit_dates._open_without_redirects", return_value=FakeResponse(final_url)
            ):
                with self.assertRaisesRegex(ValueError, "unsafe_reddit_redirect"):
                    fetch_old_reddit("https://old.reddit.com/comments/abc123/")

    def test_network_redirect_is_rejected_before_following_destination(self):
        handler = RejectRedirects()
        request = urllib.request.Request("https://old.reddit.com/comments/abc123/")
        with self.assertRaisesRegex(urllib.error.HTTPError, "reddit_redirect_rejected"):
            handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {},
                "http://127.0.0.1/internal",
            )

    def test_overflow_timestamp_becomes_unverified(self):
        html = (
            '<div class="thing" data-fullname="t3_abc123" data-timestamp="'
            + "9" * 500
            + '"></div>'
        )
        result = verify_reddit_url(
            "https://redd.it/abc123", fetcher=lambda _: html
        )
        self.assertEqual(result["status"], "unverified")
        self.assertIn("fetch_failed", result["error"])

    def test_verifies_window_and_keeps_unverified(self):
        old_html = """
        <div class="thing" data-fullname="t3_old123">
          <time datetime="2026-06-23T11:34:00+00:00">22 days ago</time>
        </div>
        """
        since = datetime(2026, 7, 9, tzinfo=timezone.utc)
        until = datetime(2026, 7, 15, tzinfo=timezone.utc)
        verified = verify_reddit_url(
            "https://www.reddit.com/r/codex/comments/old123/example/",
            since=since,
            until=until,
            fetcher=lambda _: old_html,
        )
        self.assertEqual(verified["status"], "verified")
        self.assertFalse(verified["within_window"])

        unverified = verify_reddit_url(
            "https://www.reddit.com/r/codex/comments/miss123/example/",
            since=since,
            until=until,
            fetcher=lambda _: "<html>no absolute submission date</html>",
        )
        self.assertEqual(unverified["status"], "unverified")
        self.assertIsNone(unverified["within_window"])
        self.assertEqual(unverified["error"], "absolute_date_not_found")


if __name__ == "__main__":
    unittest.main()

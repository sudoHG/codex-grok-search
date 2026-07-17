import hashlib
import os
import stat
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL_START = "<!-- BEGIN STAGED INSTALL -->"
INSTALL_END = "<!-- END STAGED INSTALL -->"
RELEASE_INSTALL_START = "<!-- BEGIN RELEASE INSTALL -->"
RELEASE_INSTALL_END = "<!-- END RELEASE INSTALL -->"
UNINSTALL_START = "<!-- BEGIN UNINSTALL -->"
UNINSTALL_END = "<!-- END UNINSTALL -->"
INSTALL_URL = (
    "https://github.com/sudoHG/codex-grok-search/tree/main/codex-grok-search"
)
RELEASE_URL = (
    "https://github.com/sudoHG/codex-grok-search/releases/tag/v0.1.2"
)
BADGE_LABELS = (
    "CI",
    "Release",
    "Downloads",
    "Stars",
    "License",
    "README views",
)


def install_script() -> str:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split(INSTALL_START, 1)[1].split(INSTALL_END, 1)[0]
    return section.split("```sh\n", 1)[1].split("\n```", 1)[0]


def release_install_script() -> str:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split(RELEASE_INSTALL_START, 1)[1].split(
        RELEASE_INSTALL_END, 1
    )[0]
    return section.split("```sh\n", 1)[1].split("\n```", 1)[0]


def uninstall_script() -> str:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split(UNINSTALL_START, 1)[1].split(UNINSTALL_END, 1)[0]
    return section.split("```sh\n", 1)[1].split("\n```", 1)[0]


def marked_script(path: Path, start: str, end: str) -> str:
    readme = path.read_text(encoding="utf-8")
    section = readme.split(start, 1)[1].split(end, 1)[0]
    return section.split("```sh\n", 1)[1].split("\n```", 1)[0]


class InstallDocumentationTests(unittest.TestCase):
    def test_skill_metadata_explicitly_routes_current_x_and_reddit_first(self):
        skill = (ROOT / "codex-grok-search" / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = skill.split("---", 2)[1]
        description = frontmatter.split("description:", 1)[1].strip()
        self.assertTrue(description.startswith("MUST use first for current X/Twitter"))
        self.assertIn("an account's latest posts", frontmatter)
        self.assertIn("recent discussions", frontmatter)
        self.assertIn("without Codex web search or browser verification", frontmatter)
        self.assertIn("Do not call Codex web search", skill)
        self.assertIn("Never use the user's personal or interactive browser", skill)

    def test_chinese_manual_commands_match_default_english_readme(self):
        chinese = ROOT / "README.zh-CN.md"
        self.assertTrue(chinese.is_file())
        for start, end in (
            (INSTALL_START, INSTALL_END),
            (RELEASE_INSTALL_START, RELEASE_INSTALL_END),
            (UNINSTALL_START, UNINSTALL_END),
        ):
            with self.subTest(marker=start):
                self.assertEqual(
                    marked_script(ROOT / "README.md", start, end),
                    marked_script(chinese, start, end),
                )

    def test_readmes_use_real_urls_without_draft_placeholders(self):
        readmes = [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "README.zh-CN.md").read_text(encoding="utf-8"),
        ]
        forbidden = (
            "<GitHub 上 codex-grok-search 目录的链接>",
            "<URL of the codex-grok-search directory on GitHub>",
            "占位内容",
            "placeholder above",
            "public GitHub repository does not exist yet",
            "Download links will be added",
            "首个 GitHub Release 发布后",
        )
        for readme in readmes:
            self.assertIn(INSTALL_URL, readme)
            self.assertIn(RELEASE_URL, readme)
            for snippet in forbidden:
                self.assertNotIn(snippet, readme)

    def test_default_readme_is_english_and_links_to_chinese(self):
        default = (ROOT / "README.md").read_text(encoding="utf-8")
        chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
        self.assertIn("[简体中文](README.zh-CN.md) | English", default)
        self.assertIn("[English](README.md) | 简体中文", chinese)
        self.assertIn("## What it can do", default)
        self.assertIn("## 它能做什么", chinese)
        self.assertFalse((ROOT / "README.en.md").exists())

    def test_readmes_share_the_same_complete_badge_row(self):
        default_lines = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
        chinese_lines = (
            (ROOT / "README.zh-CN.md").read_text(encoding="utf-8").splitlines()
        )
        badge_row = default_lines[2]
        self.assertEqual(badge_row, chinese_lines[2])
        for label in BADGE_LABELS:
            self.assertIn(f"[![{label}]", badge_row)
        self.assertIn("img.shields.io/github/actions/workflow/status", badge_row)
        self.assertIn("img.shields.io/github/v/release", badge_row)
        self.assertIn("img.shields.io/github/downloads", badge_row)
        self.assertIn("img.shields.io/github/stars", badge_row)
        self.assertIn("img.shields.io/github/license", badge_row)
        self.assertIn("hits.sh/github.com/sudoHG/codex-grok-search.svg", badge_row)

    def prepare(self, root: Path, validator_exit: int = 0):
        project = root / "project"
        source = project / "codex-grok-search"
        source.mkdir(parents=True)
        (source / "SKILL.md").write_text("new\n", encoding="utf-8")
        scripts = source / "scripts"
        scripts.mkdir()
        (scripts / "run_search.py").write_text("print('new')\n", encoding="utf-8")
        codex_home = root / "custom-codex-home"
        validator = (
            codex_home
            / "skills"
            / ".system"
            / "skill-creator"
            / "scripts"
            / "quick_validate.py"
        )
        validator.parent.mkdir(parents=True)
        validator.write_text(
            f"import sys\nraise SystemExit({validator_exit})\n", encoding="utf-8"
        )
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)
        subprocess.run(["git", "add", "codex-grok-search"], cwd=project, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=install-test",
                "-c",
                "user.email=install-test@invalid",
                "commit",
                "-qm",
                "fixture",
            ],
            cwd=project,
            check=True,
        )
        return project, codex_home

    def run_install(self, project: Path, codex_home: Path, extra_env=None):
        env = dict(os.environ, CODEX_HOME=str(codex_home))
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            ["/bin/sh", "-c", install_script()],
            cwd=project,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def prepare_release(self, root: Path, validator_exit: int = 0):
        assets = root / "assets"
        payload = root / "payload" / "codex-grok-search"
        payload.mkdir(parents=True)
        (payload / "SKILL.md").write_text("release\n", encoding="utf-8")
        scripts = payload / "scripts"
        scripts.mkdir()
        (scripts / "run_search.py").write_text("print('release')\n", encoding="utf-8")
        archive = assets / "codex-grok-search-v0.1.2.zip"
        assets.mkdir()
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.write(payload / "SKILL.md", "codex-grok-search/SKILL.md")
            bundle.write(
                payload / "scripts/run_search.py",
                "codex-grok-search/scripts/run_search.py",
            )
        tarball = assets / "codex-grok-search-v0.1.2.tar.gz"
        tarball.write_bytes(b"matching-release-fixture")
        checksums = []
        for artifact in (archive, tarball):
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            checksums.append(f"{digest}  {artifact.name}\n")
        (assets / "SHA256SUMS").write_text("".join(checksums), encoding="utf-8")

        codex_home = root / "release-codex-home"
        validator = (
            codex_home
            / "skills"
            / ".system"
            / "skill-creator"
            / "scripts"
            / "quick_validate.py"
        )
        validator.parent.mkdir(parents=True)
        validator.write_text(
            f"import sys\nraise SystemExit({validator_exit})\n", encoding="utf-8"
        )
        return assets, codex_home

    def run_release_install(self, assets: Path, codex_home: Path):
        return subprocess.run(
            ["/bin/sh", "-c", release_install_script()],
            cwd=assets,
            env=dict(os.environ, CODEX_HOME=str(codex_home)),
            text=True,
            capture_output=True,
            check=False,
        )

    def run_uninstall(self, codex_home: Path):
        return subprocess.run(
            ["/bin/sh", "-c", uninstall_script()],
            env=dict(os.environ, CODEX_HOME=str(codex_home)),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_custom_codex_home_upgrade_removes_stale_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, codex_home = self.prepare(Path(tmp))
            untracked = project / "codex-grok-search" / "__pycache__"
            untracked.mkdir()
            (untracked / "leak.pyc").write_bytes(b"untracked")
            destination = codex_home / "skills" / "codex-grok-search"
            destination.mkdir(parents=True)
            (destination / "stale.txt").write_text("old\n", encoding="utf-8")
            completed = self.run_install(project, codex_home)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual((destination / "SKILL.md").read_text(), "new\n")
            self.assertFalse((destination / "stale.txt").exists())
            self.assertFalse((destination / "__pycache__").exists())
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o755)
            self.assertEqual(stat.S_IMODE((destination / "SKILL.md").stat().st_mode), 0o644)
            self.assertEqual(
                stat.S_IMODE((destination / "scripts/run_search.py").stat().st_mode),
                0o755,
            )
            self.assertFalse(list((codex_home / "skills").glob(".codex-grok-search.*")))

    def test_validator_failure_preserves_existing_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, codex_home = self.prepare(Path(tmp), validator_exit=9)
            destination = codex_home / "skills" / "codex-grok-search"
            destination.mkdir(parents=True)
            (destination / "old.txt").write_text("preserve\n", encoding="utf-8")
            completed = self.run_install(project, codex_home)
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual((destination / "old.txt").read_text(), "preserve\n")
            self.assertFalse((destination / "SKILL.md").exists())
            self.assertFalse(list((codex_home / "skills").glob(".codex-grok-search.*")))

    def test_archive_failure_preserves_existing_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, codex_home = self.prepare(Path(tmp))
            destination = codex_home / "skills" / "codex-grok-search"
            destination.mkdir(parents=True)
            (destination / "old.txt").write_text("preserve\n", encoding="utf-8")
            (project / ".git").rename(project / "missing-git")
            completed = self.run_install(project, codex_home)
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual((destination / "old.txt").read_text(), "preserve\n")
            self.assertFalse(list((codex_home / "skills").glob(".codex-grok-search.*")))

    def test_term_during_switch_rolls_back_and_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project, codex_home = self.prepare(root)
            destination = codex_home / "skills" / "codex-grok-search"
            destination.mkdir(parents=True)
            (destination / "old.txt").write_text("preserve\n", encoding="utf-8")
            tools = root / "tools"
            tools.mkdir()
            marker = root / "interrupted"
            wrapper = tools / "mv"
            wrapper.write_text(
                "#!/bin/sh\n"
                "/bin/mv \"$@\" || exit $?\n"
                "case \"$*\" in\n"
                "  *.codex-grok-search.backup.*)\n"
                f"    if [ ! -e {str(marker)!r} ]; then /usr/bin/touch {str(marker)!r}; "
                "kill -TERM \"$PPID\"; fi ;;\n"
                "esac\n",
                encoding="utf-8",
            )
            wrapper.chmod(0o755)
            completed = self.run_install(
                project,
                codex_home,
                {"PATH": f"{tools}:{os.environ.get('PATH', '')}"},
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual((destination / "old.txt").read_text(), "preserve\n")
            self.assertFalse((destination / "SKILL.md").exists())
            self.assertFalse(list((codex_home / "skills").glob(".codex-grok-search.*")))

    def test_preexisting_legacy_backup_name_cannot_capture_old_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, codex_home = self.prepare(Path(tmp))
            skills = codex_home / "skills"
            collision = skills / ".codex-grok-search.backup.12345"
            collision.mkdir()
            (collision / "unrelated.txt").write_text("preserve\n", encoding="utf-8")
            destination = skills / "codex-grok-search"
            destination.mkdir(parents=True)
            (destination / "old.txt").write_text("old\n", encoding="utf-8")
            completed = self.run_install(project, codex_home)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual((destination / "SKILL.md").read_text(), "new\n")
            self.assertFalse((destination / "old.txt").exists())
            self.assertEqual((collision / "unrelated.txt").read_text(), "preserve\n")

    def test_install_lock_rejects_concurrent_source_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, codex_home = self.prepare(Path(tmp))
            skills = codex_home / "skills"
            lock = skills / ".codex-grok-search.install.lock"
            lock.mkdir()
            destination = skills / "codex-grok-search"
            destination.mkdir()
            (destination / "old.txt").write_text("preserve\n", encoding="utf-8")
            completed = self.run_install(project, codex_home)
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual((destination / "old.txt").read_text(), "preserve\n")
            self.assertTrue(lock.is_dir())

    def test_release_install_verifies_and_replaces_without_stale_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            assets, codex_home = self.prepare_release(Path(tmp))
            (assets / "codex-grok-search-v0.1.2.tar.gz").unlink()
            destination = codex_home / "skills" / "codex-grok-search"
            destination.mkdir(parents=True)
            (destination / "stale.txt").write_text("old\n", encoding="utf-8")
            completed = self.run_release_install(assets, codex_home)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual((destination / "SKILL.md").read_text(), "release\n")
            self.assertFalse((destination / "stale.txt").exists())
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o755)
            self.assertEqual(stat.S_IMODE((destination / "SKILL.md").stat().st_mode), 0o644)
            self.assertEqual(
                stat.S_IMODE((destination / "scripts/run_search.py").stat().st_mode),
                0o755,
            )
            self.assertFalse(list((codex_home / "skills").glob(".codex-grok-search.*")))

    def test_release_checksum_failure_preserves_existing_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            assets, codex_home = self.prepare_release(Path(tmp))
            destination = codex_home / "skills" / "codex-grok-search"
            destination.mkdir(parents=True)
            (destination / "old.txt").write_text("preserve\n", encoding="utf-8")
            archive = assets / "codex-grok-search-v0.1.2.zip"
            archive.write_bytes(archive.read_bytes() + b"tampered")
            completed = self.run_release_install(assets, codex_home)
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual((destination / "old.txt").read_text(), "preserve\n")
            self.assertFalse(list((codex_home / "skills").glob(".codex-grok-search.*")))

    def test_install_lock_rejects_concurrent_release_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            assets, codex_home = self.prepare_release(Path(tmp))
            skills = codex_home / "skills"
            destination = skills / "codex-grok-search"
            destination.mkdir(parents=True)
            (destination / "old.txt").write_text("preserve\n", encoding="utf-8")
            lock = skills / ".codex-grok-search.install.lock"
            lock.mkdir()
            completed = self.run_release_install(assets, codex_home)
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual((destination / "old.txt").read_text(), "preserve\n")
            self.assertTrue(lock.is_dir())

    def test_uninstall_uses_unique_retirement_and_preserves_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "home"
            skills = codex_home / "skills"
            destination = skills / "codex-grok-search"
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text("installed\n", encoding="utf-8")
            collision = skills / ".codex-grok-search.uninstall.12345"
            collision.mkdir()
            (collision / "user-file").write_text("preserve\n", encoding="utf-8")
            completed = self.run_uninstall(codex_home)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertFalse(destination.exists())
            self.assertEqual((collision / "user-file").read_text(), "preserve\n")
            self.assertFalse((skills / ".codex-grok-search.install.lock").exists())

    def test_uninstall_respects_active_install_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "home"
            skills = codex_home / "skills"
            destination = skills / "codex-grok-search"
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text("preserve\n", encoding="utf-8")
            lock = skills / ".codex-grok-search.install.lock"
            lock.mkdir()
            completed = self.run_uninstall(codex_home)
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual((destination / "SKILL.md").read_text(), "preserve\n")
            self.assertTrue(lock.is_dir())

    def test_all_transactions_disarm_rollback_before_releasing_lock(self):
        for name, script in (
            ("source install", install_script()),
            ("release install", release_install_script()),
            ("uninstall", uninstall_script()),
        ):
            with self.subTest(name=name):
                ignore = script.rfind("trap '' HUP INT TERM")
                disarm = script.rfind("trap - EXIT")
                unlock = script.rfind('rmdir "$install_lock"')
                restore = script.rfind("trap - HUP INT TERM")
                self.assertGreaterEqual(ignore, 0)
                self.assertGreater(disarm, ignore)
                self.assertGreater(unlock, disarm)
                self.assertGreater(restore, unlock)


if __name__ == "__main__":
    unittest.main()

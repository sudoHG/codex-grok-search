import os
import subprocess
import shutil
import stat
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_release.py"


class ReleaseBuildTests(unittest.TestCase):
    def prepare_repo(self, root: Path) -> Path:
        repo = root / "fixture-repo"
        (repo / "scripts").mkdir(parents=True)
        shutil.copy2(BUILDER, repo / "scripts/build_release.py")
        shutil.copytree(
            ROOT / "codex-grok-search",
            repo / "codex-grok-search",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "scripts", "codex-grok-search"], cwd=repo, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=release-test",
                "-c",
                "user.email=release-test@invalid",
                "commit",
                "-qm",
                "fixture",
            ],
            cwd=repo,
            check=True,
        )
        return repo

    def build(self, repo: Path, output: Path, tar_umask: str):
        env = dict(os.environ)
        env.update(
            {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "tar.umask",
                "GIT_CONFIG_VALUE_0": tar_umask,
            }
        )
        return subprocess.run(
            [
                sys.executable,
                str(repo / "scripts/build_release.py"),
                "--commit",
                "HEAD",
                "--version",
                "v0.1.0-rc.2",
                "--output-dir",
                str(output),
            ],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_release_build_is_deterministic_and_self_verifying(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self.prepare_repo(root)
            first = root / "first"
            second = root / "second"
            one = self.build(repo, first, "0002")
            two = self.build(repo, second, "0022")
            self.assertEqual(one.returncode, 0, one.stderr)
            self.assertEqual(two.returncode, 0, two.stderr)
            names = (
                "codex-grok-search-v0.1.0-rc.2.zip",
                "codex-grok-search-v0.1.0-rc.2.tar.gz",
                "SHA256SUMS",
            )
            for name in names:
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
            completed = subprocess.run(
                ["shasum", "-a", "256", "-c", "SHA256SUMS"],
                cwd=first,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            with zipfile.ZipFile(first / names[0]) as zip_bundle, tarfile.open(
                first / names[1], "r:gz"
            ) as tar_bundle:
                zip_files = {
                    item.filename: zip_bundle.read(item.filename)
                    for item in zip_bundle.infolist()
                    if not item.is_dir()
                }
                tar_files = {
                    item.name: tar_bundle.extractfile(item).read()
                    for item in tar_bundle.getmembers()
                    if item.isfile()
                }
                zip_modes = {
                    item.filename: stat.S_IMODE(item.external_attr >> 16)
                    for item in zip_bundle.infolist()
                }
                tar_modes = {
                    item.name.rstrip("/") + ("/" if item.isdir() else ""): stat.S_IMODE(item.mode)
                    for item in tar_bundle.getmembers()
                }
            self.assertEqual(zip_files, tar_files)
            self.assertEqual(zip_modes, tar_modes)
            self.assertTrue(
                all(
                    mode == (0o755 if name.endswith("/") or name.endswith(".py") else 0o644)
                    for name, mode in zip_modes.items()
                )
            )
            self.assertTrue(all(name.startswith("codex-grok-search/") for name in zip_files))
            self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in zip_files))

    def test_release_builder_rejects_bad_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(BUILDER),
                    "--version",
                    "../../bad",
                    "--output-dir",
                    tmp,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)


if __name__ == "__main__":
    unittest.main()

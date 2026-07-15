#!/usr/bin/env python3
"""Build deterministic codex-grok-search Release archives from a Git commit."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import re
import subprocess
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


SKILL_ROOT = "codex-grok-search"
VERSION_RE = re.compile(r"v\d+\.\d+\.\d+(?:-[0-9a-z]+(?:\.[0-9a-z]+)*)?\Z")
FIXED_MTIME = 1577836800
FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)


@dataclass(frozen=True)
class Entry:
    name: str
    mode: int
    is_dir: bool
    data: bytes


def git_output(repo: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, check=False
    )
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(message or f"git {' '.join(args)} failed")
    return completed.stdout


def resolve_commit(repo: Path, value: str) -> str:
    return git_output(repo, "rev-parse", "--verify", f"{value}^{{commit}}").decode().strip()


def committed_file_modes(repo: Path, commit: str) -> dict[str, int]:
    tree = git_output(
        repo, "ls-tree", "-rz", "--full-tree", commit, "--", SKILL_ROOT
    )
    modes: dict[str, int] = {}
    for record in tree.split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, object_type, _object_id = metadata.decode("ascii").split(" ", 2)
        path = raw_path.decode("utf-8")
        if object_type != "blob" or mode not in {"100644", "100755"}:
            raise RuntimeError(f"unsupported Git tree entry: {mode} {object_type} {path}")
        modes[path] = 0o755 if mode == "100755" else 0o644
    return modes


def committed_entries(repo: Path, commit: str) -> list[Entry]:
    file_modes = committed_file_modes(repo, commit)
    archive = git_output(repo, "archive", "--format=tar", commit, SKILL_ROOT)
    entries: list[Entry] = []
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
        for member in bundle.getmembers():
            path = PurePosixPath(member.name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or not path.parts
                or path.parts[0] != SKILL_ROOT
            ):
                raise RuntimeError(f"unsafe archive path: {member.name}")
            if not (member.isdir() or member.isfile()):
                raise RuntimeError(f"unsupported archive entry: {member.name}")
            name = member.name.rstrip("/") + ("/" if member.isdir() else "")
            extracted = bundle.extractfile(member) if member.isfile() else None
            data = extracted.read() if extracted is not None else b""
            if member.isdir():
                mode = 0o755
            else:
                try:
                    mode = file_modes.pop(member.name)
                except KeyError as exc:
                    raise RuntimeError(f"archive file missing from Git tree: {member.name}") from exc
            entries.append(Entry(name, mode, member.isdir(), data))
    if not entries or entries[0].name != f"{SKILL_ROOT}/":
        raise RuntimeError("Git archive does not contain the expected Skill root")
    if file_modes:
        raise RuntimeError("Git tree files are missing from the archive")
    return sorted(entries, key=lambda item: item.name)


def build_zip(entries: list[Entry]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(
        output, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as bundle:
        for entry in entries:
            info = zipfile.ZipInfo(entry.name, FIXED_ZIP_TIME)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_STORED if entry.is_dir else zipfile.ZIP_DEFLATED
            file_type = 0o040000 if entry.is_dir else 0o100000
            info.external_attr = ((file_type | entry.mode) & 0xFFFF) << 16
            if entry.is_dir:
                info.external_attr |= 0x10
            bundle.writestr(info, entry.data, compress_type=info.compress_type, compresslevel=9)
    return output.getvalue()


def build_tar_gz(entries: list[Entry]) -> bytes:
    tar_output = io.BytesIO()
    with tarfile.open(fileobj=tar_output, mode="w", format=tarfile.USTAR_FORMAT) as bundle:
        for entry in entries:
            info = tarfile.TarInfo(entry.name.rstrip("/") if entry.is_dir else entry.name)
            info.type = tarfile.DIRTYPE if entry.is_dir else tarfile.REGTYPE
            info.mode = entry.mode
            info.uid = 0
            info.gid = 0
            info.uname = "root"
            info.gname = "root"
            info.mtime = FIXED_MTIME
            info.size = 0 if entry.is_dir else len(entry.data)
            bundle.addfile(info, None if entry.is_dir else io.BytesIO(entry.data))
    compressed = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0) as stream:
        stream.write(tar_output.getvalue())
    return compressed.getvalue()


def atomic_write(path: Path, data: bytes) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
    temporary.chmod(0o644)
    temporary.replace(path)


def build_release(repo: Path, commit: str, version: str, output_dir: Path) -> dict[str, str]:
    if not VERSION_RE.fullmatch(version):
        raise ValueError("version must look like v0.1.0 or v0.1.0-rc.2")
    resolved = resolve_commit(repo, commit)
    entries = committed_entries(repo, resolved)
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_name = f"codex-grok-search-{version}.zip"
    tar_name = f"codex-grok-search-{version}.tar.gz"
    artifacts = {
        zip_name: build_zip(entries),
        tar_name: build_tar_gz(entries),
    }
    for name, content in artifacts.items():
        atomic_write(output_dir / name, content)
    checksums = "".join(
        f"{hashlib.sha256(content).hexdigest()}  {name}\n"
        for name, content in artifacts.items()
    ).encode("utf-8")
    atomic_write(output_dir / "SHA256SUMS", checksums)
    return {"commit": resolved, "zip": zip_name, "tar_gz": tar_name}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    result = build_release(repo, args.commit, args.version, args.output_dir.resolve())
    print(f"commit={result['commit']}")
    print(f"zip={result['zip']}")
    print(f"tar_gz={result['tar_gz']}")
    print("checksums=SHA256SUMS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

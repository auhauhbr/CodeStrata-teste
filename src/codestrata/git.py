from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator


class GitError(RuntimeError):
    pass


@dataclass(slots=True, frozen=True)
class Commit:
    sha: str
    committed_at: datetime
    subject: str


class GitRepository:
    """Read-only adapter around a local Git checkout."""

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path).resolve()
        if not (self.path / ".git").exists():
            probe = self._run("rev-parse", "--git-dir", check=False)
            if probe.returncode != 0:
                raise GitError(f"Not a Git repository: {self.path}")

    def _run(
        self,
        *args: str,
        check: bool = True,
        text: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", "-C", str(self.path), *args],
            capture_output=True,
            text=text,
            check=False,
        )
        if check and result.returncode != 0:
            message = (result.stderr or result.stdout).strip()
            raise GitError(message or f"git {' '.join(args)} failed")
        return result

    @property
    def display_name(self) -> str:
        remote = self._run("remote", "get-url", "origin", check=False)
        if remote.returncode == 0 and remote.stdout.strip():
            return remote.stdout.strip()
        return self.path.name

    def head_sha(self) -> str:
        return self._run("rev-parse", "HEAD").stdout.strip()

    def commits(self) -> list[Commit]:
        raw = self._run(
            "log",
            "--reverse",
            "--date=iso-strict",
            "--format=%H%x1f%cI%x1f%s%x1e",
        ).stdout
        commits: list[Commit] = []
        for record in raw.split("\x1e"):
            record = record.strip("\n")
            if not record.strip():
                continue
            parts = record.split("\x1f", 2)
            if len(parts) != 3:
                continue
            sha, committed_at, subject = parts
            commits.append(
                Commit(
                    sha=sha.strip(),
                    committed_at=datetime.fromisoformat(committed_at.strip()),
                    subject=subject.strip(),
                )
            )
        return commits

    def commit(self, ref: str) -> Commit:
        raw = self._run(
            "show",
            "-s",
            "--date=iso-strict",
            "--format=%H%x1f%cI%x1f%s",
            ref,
        ).stdout.strip()
        sha, committed_at, subject = raw.split("\x1f", 2)
        return Commit(sha, datetime.fromisoformat(committed_at), subject)

    def list_files(self, ref: str) -> list[str]:
        raw = self._run("ls-tree", "-r", "--name-only", ref).stdout
        return [line for line in raw.splitlines() if line]

    def read_file(self, ref: str, path: str, *, max_bytes: int = 512_000) -> str | None:
        size_result = self._run("cat-file", "-s", f"{ref}:{path}", check=False)
        if size_result.returncode != 0:
            return None
        with contextlib.suppress(ValueError):
            if int(size_result.stdout.strip()) > max_bytes:
                return None
        result = subprocess.run(
            ["git", "-C", str(self.path), "show", f"{ref}:{path}"],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0 or b"\x00" in result.stdout[:4096]:
            return None
        return result.stdout.decode("utf-8", errors="replace")


@contextlib.contextmanager
def open_repository(source: str) -> Iterator[GitRepository]:
    """Open a local repository or temporarily clone a remote URL."""

    local = Path(source).expanduser()
    if local.exists():
        yield GitRepository(local)
        return

    if not source.startswith(("http://", "https://", "git@")):
        raise GitError(f"Repository path does not exist: {source}")

    temp_dir = Path(tempfile.mkdtemp(prefix="codestrata-"))
    try:
        target = temp_dir / "repo"
        result = subprocess.run(
            ["git", "clone", "--quiet", "--filter=blob:none", source, str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise GitError(result.stderr.strip() or f"Could not clone {source}")
        yield GitRepository(target)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

"""
Repository Cloner.
Shallow clones remote Git repositories or verifies local repository paths.

Two properties matter beyond "get the files here":

1. The caller may pick a branch or tag. When it does not, the remote's own
   default branch decides — never a hardcoded `main`/`master`.
2. The clone reports exactly what it checked out (ref + commit), so the
   generated wiki can state which revision it documents.

Local paths are accepted so the demo fixtures can be ingested offline, but a
name collision between two different sources is an error here rather than a
silent overwrite in `content/`.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse


class RepoNameCollisionError(ValueError):
    """Two different sources resolve to the same wiki line name."""


def sanitize_repo_name(raw_name: str) -> str:
    """Sanitize repository name to safe identifier (alphanumerics, dashes, underscores)."""
    # Remove .git suffix if present
    name = re.sub(r"\.git$", "", raw_name.strip(), flags=re.IGNORECASE)
    # Extract last segment if path-like
    name = name.rstrip("/\\").split("/")[-1].split("\\")[-1]
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "-", name).strip("-")
    if not cleaned or cleaned in (".", ".."):
        raise ValueError(f"Invalid or unsafe repository name derived from: '{raw_name}'")
    return cleaned


def _split_owner_and_repo(clean: str) -> Optional[Tuple[str, str]]:
    """
    Returns (owner, repo) for a remote-looking source, else None.

    Only the two-positional-segment forms are treated as remote: `host/owner/repo`
    and the scp-style `git@host:owner/repo`. A bare local path has no owner, and
    inventing one would rename every fixture on disk.
    """
    ssh_match = re.match(r"^[^/@]+@[^/:]+:([^/]+)/([^/]+?)(?:\.git)?/?$", clean)
    if ssh_match:
        return ssh_match.group(1), ssh_match.group(2)

    parsed = urlparse(clean)
    if parsed.scheme in ("http", "https", "ssh", "git") or parsed.netloc:
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2:
            return parts[-2], parts[-1]
    return None


def extract_repo_name_from_source(source: str, include_owner: bool = False) -> str:
    """
    Derive repository name from Git URL or local folder path.

    `include_owner=True` prefixes the owner (`org1/api` -> `org1-api`), which is
    the only way to keep same-named repositories from different owners apart.
    """
    source_clean = source.strip().rstrip("/\\")
    if not source_clean:
        raise ValueError("Source URL or path cannot be empty")
    if source_clean.startswith("-"):
        # A leading dash is parsed as a git option, not a repository.
        raise ValueError(f"Refusing to treat a command-line flag as a source: '{source}'")

    owner_and_repo = _split_owner_and_repo(source_clean)
    if owner_and_repo and include_owner:
        owner, repo = owner_and_repo
        return sanitize_repo_name(f"{owner}-{repo}")

    if owner_and_repo:
        return sanitize_repo_name(owner_and_repo[1])

    # Check for git SSH style: git@github.com:org/repo.git
    ssh_match = re.search(r":([^/]+/[^/]+?)(?:\.git)?$", source_clean)
    if ssh_match:
        part = ssh_match.group(1).split("/")[-1]
        return sanitize_repo_name(part)

    # Standard URL or file path
    parsed = urlparse(source_clean)
    if parsed.path:
        base = parsed.path.rstrip("/").split("/")[-1]
        if base:
            return sanitize_repo_name(base)

    return sanitize_repo_name(source_clean)


@dataclass(frozen=True)
class RefListing:
    """What a remote advertises, for populating a branch picker."""

    default_branch: Optional[str]
    branches: List[str]
    tags: List[str]

    def to_dict(self) -> dict:
        return {
            "default_branch": self.default_branch,
            "branches": self.branches,
            "tags": self.tags,
        }


@dataclass(frozen=True)
class CloneResult:
    """A checked-out tree plus the revision it actually came from."""

    repo_name: str
    repo_dir: Path
    source: str
    ref: Optional[str]
    branch: Optional[str]
    commit: Optional[str]

    @property
    def short_commit(self) -> Optional[str]:
        return self.commit[:7] if self.commit else None

    @property
    def provenance(self) -> dict:
        """Fields merged into the wiki's `toc.json`."""
        return {
            "source": self.source,
            "ref": self.ref or self.branch,
            "branch": self.branch,
            "commit": self.commit,
        }

    def __iter__(self):
        """Keeps `name, path = cloner.clone(...)` working."""
        return iter((self.repo_name, self.repo_dir))


def _git(args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """
    Runs git without a terminal attached.

    `GIT_TERMINAL_PROMPT=0` turns a private repository into a fast, explicit
    failure instead of a hung request waiting on a username prompt.
    """
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "true"}
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
    )


class RepoCloner:
    def __init__(self, temp_dir: str | Path, content_dir: Optional[str | Path] = None):
        self.temp_dir = Path(temp_dir).resolve()
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.content_dir = Path(content_dir).resolve() if content_dir else None

    def resolve_local_path(self, source: str) -> Optional[Path]:
        """Check if source refers to an existing local directory or seeded repo."""
        path = Path(source).expanduser()
        if path.exists() and path.is_dir():
            return path.resolve()
        if self.content_dir:
            cand = self.content_dir / source
            if cand.exists() and cand.is_dir():
                return cand.resolve()
        return None

    def is_local_path(self, source: str) -> bool:
        """Check if source refers to an existing local directory."""
        return self.resolve_local_path(source) is not None

    # -- ref discovery -----------------------------------------------------

    def list_refs(self, source: str, timeout: int = 20) -> RefListing:
        """
        Lists the branches and tags a remote advertises, plus its default branch.

        One `ls-remote` call answers both questions, and works without cloning.
        Local directories are read from their own git repository.
        """
        if self.is_local_path(source):
            return self._list_local_refs(source)

        res = _git(["ls-remote", "--symref", "--", source.strip()], timeout=timeout)
        if res.returncode != 0:
            # First stderr line only: git repeats the same failure across lines.
            detail = next(
                (line.strip() for line in res.stderr.splitlines() if line.strip()),
                "git ls-remote failed",
            ).rstrip(".")
            raise RuntimeError(f"Could not list refs for {source.strip()}: {detail}")

        default_branch: Optional[str] = None
        branches: List[str] = []
        tags: List[str] = []

        for line in res.stdout.splitlines():
            if line.startswith("ref:"):
                # `ref: refs/heads/main\tHEAD`
                target = line[4:].split("\t")[0].strip()
                if target.startswith("refs/heads/"):
                    default_branch = target[len("refs/heads/"):]
                continue
            parts = line.split("\t")
            if len(parts) != 2:
                continue
            ref = parts[1].strip()
            if ref.startswith("refs/heads/"):
                branches.append(ref[len("refs/heads/"):])
            elif ref.startswith("refs/tags/") and not ref.endswith("^{}"):
                tags.append(ref[len("refs/tags/"):])

        return RefListing(
            default_branch=default_branch,
            branches=sorted(branches),
            tags=sorted(tags),
        )

    def _list_local_refs(self, source: str) -> RefListing:
        """Reads refs from a local checkout; empty listing when it is not a repo."""
        local = self.resolve_local_path(source)
        if local is None:
            return RefListing(default_branch=None, branches=[], tags=[])

        # A seeded wiki line is not a git checkout, so there is nothing to list.
        if not (local / ".git").exists():
            return RefListing(default_branch=None, branches=[], tags=[])

        branches = _git(["-C", str(local), "for-each-ref", "--format=%(refname:short)", "refs/heads"])
        tags = _git(["-C", str(local), "for-each-ref", "--format=%(refname:short)", "refs/tags"])
        head = _git(["-C", str(local), "rev-parse", "--abbrev-ref", "HEAD"])

        branch_names = [b for b in branches.stdout.split() if b]
        return RefListing(
            default_branch=head.stdout.strip() if head.returncode == 0 else None,
            branches=sorted(branch_names),
            tags=sorted(t for t in tags.stdout.split() if t),
        )

    # -- collision guarding ------------------------------------------------

    def _existing_source(self, repo_name: str) -> Optional[str]:
        """The `source` recorded for an already-published wiki line, if any."""
        if self.content_dir is None:
            return None
        toc_path = self.content_dir / repo_name / "toc.json"
        if not toc_path.exists():
            return None
        try:
            import json

            data = json.loads(toc_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return data.get("source") or None

    def resolve_repo_name(
        self,
        source: str,
        name: Optional[str] = None,
        prefer_owner: bool = False,
    ) -> str:
        """
        Picks the wiki line name for a source, and refuses to reuse one that
        already belongs to a different repository.

        The readable repository name is preferred, because renaming every line
        to `owner-repo` would churn existing URLs. The owner is added only when
        the plain name is already taken by a different source — which is the
        case this guards: `github.com/org1/api` and `github.com/org2/api` are
        distinct projects whose names would otherwise overwrite each other in
        `content/`.

        `prefer_owner=True` starts from the qualified name instead, for callers
        that know the line is shared.
        """
        normalized = source.strip().rstrip("/\\")

        if name and name.strip():
            candidate = sanitize_repo_name(name)
            existing = self._existing_source(candidate)
            if existing is None or existing == normalized:
                return candidate
            raise RepoNameCollisionError(
                f"Repository name '{candidate}' is already documented from a "
                f"different source ({existing})."
            )

        if prefer_owner:
            qualified = extract_repo_name_from_source(source, include_owner=True)
            existing = self._existing_source(qualified)
            if existing is None or existing == normalized:
                return qualified
            raise RepoNameCollisionError(
                f"Repository name '{qualified}' is already documented from a "
                f"different source ({existing})."
            )

        candidate = extract_repo_name_from_source(source)
        existing = self._existing_source(candidate)
        if existing is None or existing == normalized:
            return candidate

        # The plain name belongs to another repository. Qualify with the owner
        # rather than failing, so same-named projects can coexist.
        qualified = extract_repo_name_from_source(source, include_owner=True)
        if qualified != candidate:
            existing_qualified = self._existing_source(qualified)
            if existing_qualified is None or existing_qualified == normalized:
                return qualified

        raise RepoNameCollisionError(
            f"Repository name '{candidate}' is already documented from a different "
            f"source ({existing}). Pass an explicit name to ingest this repository."
        )

    # -- clone -------------------------------------------------------------

    def clone(
        self,
        source: str,
        branch: Optional[str] = None,
        force_clean: bool = True,
        name: Optional[str] = None,
    ) -> CloneResult:
        """
        Shallow clones remote Git repository into temp_dir/<repo_name>,
        or copies/points to existing local directory.

        `branch` accepts a branch or a tag. When omitted, the remote's default
        branch is checked out.
        """
        source = source.strip()
        if not source:
            raise ValueError("Repository source URL or path cannot be empty")

        repo_name = self.resolve_repo_name(source, name=name)

        local_src = self.resolve_local_path(source)
        if local_src is not None:
            target_dir = self.temp_dir / repo_name
            if force_clean and target_dir.exists() and target_dir != local_src:
                shutil.rmtree(target_dir, ignore_errors=True)
            if not target_dir.exists():
                # Copy local repo into temp folder
                shutil.copytree(
                    local_src,
                    target_dir,
                    ignore=shutil.ignore_patterns(".git", "node_modules", "dist", "build", ".venv", "venv"),
                )
            commit, local_branch = self._local_revision(local_src)
            return CloneResult(
                repo_name=repo_name,
                repo_dir=target_dir,
                source=source,
                ref=branch,
                branch=branch or local_branch,
                commit=commit,
            )

        # Remote Git repository
        target_dir = self.temp_dir / repo_name
        if force_clean and target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)

        # `--` ends option parsing: a source or path that begins with a dash is
        # then a (failing) pathname rather than a git flag.
        cmd = ["clone", "--depth", "1"]
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend(["--", source, str(target_dir)])

        try:
            res = _git(cmd, timeout=120)
            if res.returncode != 0:
                raise RuntimeError(
                    f"Git clone failed (exit code {res.returncode}): {res.stderr.strip()}"
                )
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Git clone timed out after 120s for {source}")

        if not target_dir.exists():
            raise RuntimeError(f"Cloned directory does not exist at {target_dir}")

        commit, actual_branch = self._local_revision(target_dir)
        return CloneResult(
            repo_name=repo_name,
            repo_dir=target_dir,
            source=source,
            ref=branch,
            # A tag clone lands in detached HEAD, so the requested ref is the
            # only accurate label; `branch` stays None in that case.
            branch=branch if branch and actual_branch in (None, "HEAD") else actual_branch,
            commit=commit,
        )

    def _local_revision(self, repo_dir: Path) -> Tuple[Optional[str], Optional[str]]:
        """(commit, branch) for a checkout; (None, None) when it is not a repo."""
        if not (repo_dir / ".git").exists():
            return None, None
        head = _git(["-C", str(repo_dir), "rev-parse", "HEAD"], timeout=15)
        commit = head.stdout.strip() if head.returncode == 0 else None
        ref = _git(["-C", str(repo_dir), "rev-parse", "--abbrev-ref", "HEAD"], timeout=15)
        branch = ref.stdout.strip() if ref.returncode == 0 else None
        if not branch or branch in ("HEAD", ""):
            branch = None
        return commit, branch

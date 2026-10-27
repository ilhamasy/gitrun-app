"""
Repository Cloner.
Shallow clones remote Git repositories or verifies local repository paths.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse


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


def extract_repo_name_from_source(source: str) -> str:
    """Derive repository name from Git URL or local folder path."""
    source_clean = source.strip().rstrip("/\\")
    if not source_clean:
        raise ValueError("Source URL or path cannot be empty")

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
    def clone(
        self,
        source: str,
        branch: Optional[str] = None,
        force_clean: bool = True,
    ) -> Tuple[str, Path]:
        """
        Shallow clones remote Git repository into temp_dir/<repo_name>,
        or copies/points to existing local directory.
        Returns (repo_name, repo_dir).
        """
        source = source.strip()
        if not source:
            raise ValueError("Repository source URL or path cannot be empty")

        repo_name = extract_repo_name_from_source(source)

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
            return repo_name, target_dir

        # Remote Git repository
        target_dir = self.temp_dir / repo_name
        if force_clean and target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)

        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend([source, str(target_dir)])

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if res.returncode != 0:
                raise RuntimeError(
                    f"Git clone failed (exit code {res.returncode}): {res.stderr.strip()}"
                )
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Git clone timed out after 120s for {source}")

        if not target_dir.exists():
            raise RuntimeError(f"Cloned directory does not exist at {target_dir}")

        return repo_name, target_dir

"""
Repomix Codebase Bundler.
Packs repository source trees into token-efficient XML skeletons for LLM analysis.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DEFAULT_IGNORE = (
    "**/node_modules/**,"
    "**/.git/**,"
    "**/dist/**,"
    "**/build/**,"
    "**/.next/**,"
    "**/*lock*,"
    "**/*.png,"
    "**/*.jpg,"
    "**/*.jpeg,"
    "**/*.svg,"
    "**/*.ico,"
    "**/*.woff*,"
    "**/*.pdf,"
    "**/*.zip,"
    "**/*.tar*,"
    "**/*_test.go,"
    "**/*.spec.ts,"
    "**/*.test.ts,"
    "**/*.test.js,"
    "**/venv/**,"
    "**/.venv/**"
)

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff", ".woff2",
    ".ttf", ".eot", ".mp4", ".mp3", ".zip", ".tar", ".gz", ".7z",
    ".pdf", ".exe", ".dll", ".so", ".dylib", ".bin", ".pyc", ".class",
}


class RepomixBundler:
    def __init__(self, temp_dir: str | Path):
        self.temp_dir = Path(temp_dir).resolve()
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def bundle(
        self,
        repo_dir: str | Path,
        repo_name: str,
        ignore_patterns: str = DEFAULT_IGNORE,
        timeout: int = 120,
    ) -> Path:
        """
        Runs Repomix to generate an XML bundle at temp/<repo_name>-bundle.xml.
        Falls back to internal deterministic bundler if Repomix fails or is unavailable.
        """
        repo_path = Path(repo_dir).resolve()
        if not repo_path.is_dir():
            raise FileNotFoundError(f"Repository directory does not exist: {repo_path}")

        bundle_path = self.temp_dir / f"{repo_name}-bundle.xml"
        if bundle_path.exists():
            bundle_path.unlink()

        # Try Repomix CLI first
        repomix_ok = self._run_repomix(
            repo_path=repo_path,
            output_file=bundle_path,
            ignore_patterns=ignore_patterns,
            timeout=timeout,
        )

        if not repomix_ok or not bundle_path.exists() or bundle_path.stat().st_size == 0:
            # Fallback to internal tree bundler
            self._fallback_bundle(repo_path, bundle_path)

        return bundle_path

    def _run_repomix(
        self,
        repo_path: Path,
        output_file: Path,
        ignore_patterns: str,
        timeout: int,
    ) -> bool:
        cmd = [
            "npx",
            "--yes",
            "repomix",
            "--style",
            "xml",
            "--output",
            str(output_file),
            "--ignore",
            ignore_patterns,
        ]

        try:
            res = subprocess.run(
                cmd,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return res.returncode == 0 and output_file.exists()
        except Exception:
            return False

    def _fallback_bundle(self, repo_path: Path, output_file: Path) -> None:
        """
        Deterministic lightweight XML bundler when Repomix is unavailable.
        """
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<repository name="{repo_path.name}">',
            "  <summary>Codebase bundle extracted by GoWiki</summary>",
        ]

        ignore_names = {
            ".git", "node_modules", "dist", "build", ".next", "venv", ".venv",
            "__pycache__", ".turbo", ".cache", ".idea", ".vscode",
        }

        file_count = 0
        total_bytes = 0
        max_total_bytes = 2_000_000  # Cap bundle size to ~2MB for token budget
        max_single_file = 150_000

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in ignore_names and not d.startswith(".")]

            for file_name in sorted(files):
                if file_name.startswith(".") or file_name.endswith(".lock"):
                    continue
                ext = os.path.splitext(file_name)[1].lower()
                if ext in BINARY_EXTENSIONS:
                    continue

                full_path = Path(root) / file_name
                rel_path = full_path.relative_to(repo_path)

                try:
                    file_size = full_path.stat().st_size
                    if file_size > max_single_file or total_bytes + file_size > max_total_bytes:
                        continue

                    content = full_path.read_text(encoding="utf-8", errors="replace")
                    lines.append(f'  <file path="{rel_path}">')
                    lines.append(content)
                    lines.append("  </file>")

                    file_count += 1
                    total_bytes += len(content)
                except Exception:
                    continue

        lines.append("</repository>")
        output_file.write_text("\n".join(lines), encoding="utf-8")

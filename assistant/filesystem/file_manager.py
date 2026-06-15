"""
file_manager.py — Safe Finder and file system operations for JARVIS.
All destructive operations require explicit verbal confirmation before executing.
"""

import os
import shutil
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Common spoken folder names → actual paths
FOLDER_MAP = {
    "downloads": Path.home() / "Downloads",
    "documents": Path.home() / "Documents",
    "desktop": Path.home() / "Desktop",
    "pictures": Path.home() / "Pictures",
    "movies": Path.home() / "Movies",
    "music": Path.home() / "Music",
    "home": Path.home(),
    "applications": Path("/Applications"),
}

DESTRUCTIVE_COMMANDS = {"delete", "remove", "trash", "erase"}


class FileManager:
    """
    Safe file system operations with a verbal confirmation gate
    for destructive actions.
    """

    def __init__(self, confirm_fn=None):
        """
        confirm_fn: callable(prompt_str) → bool
        Should speak the prompt and listen for "yes"/"confirm"/"proceed".
        If None, destructive ops are blocked.
        """
        self._confirm = confirm_fn

    # ── Navigation ────────────────────────────────────────────────────────────

    def open_folder(self, name: str) -> str:
        """Open a folder in Finder."""
        path = FOLDER_MAP.get(name.lower().strip(), Path.home() / name)
        if not path.exists():
            return f"I couldn't find a folder called {name}."
        subprocess.run(["open", str(path)], timeout=5)
        return f"Opening {name} in Finder."

    def show_recent_files(self) -> str:
        """Open Recents in Finder."""
        subprocess.run(["open", "recents://"], timeout=5)
        return "Opening recent files in Finder."

    # ── Creation ──────────────────────────────────────────────────────────────

    def create_folder(self, name: str, location: str = "desktop") -> str:
        """Create a new folder at the specified location."""
        base = FOLDER_MAP.get(location.lower(), Path.home() / "Desktop")
        target = base / name
        try:
            target.mkdir(parents=True, exist_ok=False)
            subprocess.run(["open", str(base)], timeout=5)
            return f"Folder '{name}' created on {location.title()}."
        except FileExistsError:
            return f"A folder named '{name}' already exists there."
        except Exception as e:
            logger.error(f"create_folder error: {e}")
            return f"Could not create folder '{name}'."

    def create_file(self, name: str, location: str = "desktop") -> str:
        """Create an empty file at the specified location."""
        base = FOLDER_MAP.get(location.lower(), Path.home() / "Desktop")
        target = base / name
        try:
            target.touch(exist_ok=False)
            return f"File '{name}' created on {location.title()}."
        except FileExistsError:
            return f"A file named '{name}' already exists there."
        except Exception as e:
            logger.error(f"create_file error: {e}")
            return f"Could not create file '{name}'."

    # ── Search ────────────────────────────────────────────────────────────────

    def search_file(self, name: str) -> str:
        """Search for a file using macOS mdfind (Spotlight)."""
        try:
            result = subprocess.run(
                ["mdfind", "-name", name],
                capture_output=True, text=True, timeout=10
            )
            lines = [l for l in result.stdout.strip().splitlines() if l]
            if not lines:
                return f"No files found matching '{name}'."
            top = lines[:3]
            return f"Found {len(lines)} file(s) named '{name}'. Top results: " + "; ".join(top)
        except Exception as e:
            logger.error(f"search_file error: {e}")
            return f"Search failed for '{name}'."

    # ── Rename / Move / Copy ──────────────────────────────────────────────────

    def rename_file(self, old_path: str, new_name: str) -> str:
        """Rename a file or folder."""
        src = Path(old_path)
        dst = src.parent / new_name
        if not src.exists():
            return f"I can't find '{old_path}'."
        try:
            src.rename(dst)
            return f"Renamed to '{new_name}'."
        except Exception as e:
            logger.error(f"rename_file error: {e}")
            return "Could not rename the file."

    def move_file(self, src_path: str, dst_folder: str) -> str:
        """Move a file to a destination folder."""
        src = Path(src_path)
        dst_base = FOLDER_MAP.get(dst_folder.lower(), Path(dst_folder))
        if not src.exists():
            return f"I can't find '{src_path}'."
        try:
            shutil.move(str(src), str(dst_base / src.name))
            return f"Moved '{src.name}' to {dst_folder}."
        except Exception as e:
            logger.error(f"move_file error: {e}")
            return "Could not move the file."

    def copy_file(self, src_path: str, dst_folder: str) -> str:
        """Copy a file to a destination folder."""
        src = Path(src_path)
        dst_base = FOLDER_MAP.get(dst_folder.lower(), Path(dst_folder))
        if not src.exists():
            return f"I can't find '{src_path}'."
        try:
            shutil.copy2(str(src), str(dst_base / src.name))
            return f"Copied '{src.name}' to {dst_folder}."
        except Exception as e:
            logger.error(f"copy_file error: {e}")
            return "Could not copy the file."

    # ── Destructive (confirmation required) ──────────────────────────────────

    def delete_file(self, path: str) -> str:
        """
        Move a file to Trash. Requires verbal confirmation.
        Uses macOS 'trash' AppleScript to safely move to Trash (recoverable).
        """
        target = Path(path)
        if not target.exists():
            return f"I can't find '{path}'."

        if self._confirm is None:
            return "Destructive operations require a confirmation handler to be set."

        confirmed = self._confirm(
            f"Are you sure you want to delete '{target.name}'? Say yes, confirm, or proceed."
        )
        if not confirmed:
            return "Deletion cancelled."

        try:
            # Move to Trash (recoverable) via AppleScript
            script = f'tell application "Finder" to delete POSIX file "{target.resolve()}"'
            subprocess.run(["osascript", "-e", script], timeout=10)
            return f"'{target.name}' has been moved to Trash."
        except Exception as e:
            logger.error(f"delete_file error: {e}")
            return "Could not delete the file."

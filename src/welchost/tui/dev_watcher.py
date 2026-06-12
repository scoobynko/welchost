"""DEV-mode hot reload: restart the app when a source file changes.

Only imported and started when DEV_MODE is active (see app.run). Never in
production.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class ReloadHandler(FileSystemEventHandler):
    def on_modified(self, event) -> None:  # noqa: ANN001
        src = getattr(event, "src_path", "")
        if isinstance(src, str) and src.endswith(".py"):
            # Re-exec the same command, then exit this process.
            subprocess.Popen([sys.executable, "-m", "welchost", *sys.argv[1:]])
            sys.exit(0)


def start_watcher() -> Observer:
    """Watch src/welchost/ for .py changes and restart on edit."""
    watch_dir = Path(__file__).resolve().parents[1]
    observer = Observer()
    observer.schedule(ReloadHandler(), str(watch_dir), recursive=True)
    observer.daemon = True
    observer.start()
    return observer

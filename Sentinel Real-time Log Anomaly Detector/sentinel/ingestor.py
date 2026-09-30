import os
import queue
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class _LogEventHandler(FileSystemEventHandler):
    def __init__(self, filepath, event_queue):
        super().__init__()
        self.filepath = Path(filepath).absolute()
        self.event_queue = event_queue

    def on_modified(self, event):
        if Path(event.src_path).absolute() == self.filepath:
            self.event_queue.put("modified")

    def on_created(self, event):
        if Path(event.src_path).absolute() == self.filepath:
            self.event_queue.put("created")


class LogTailer:
    """
    Tails a log file in real-time, yielding lines as they are appended.
    Supports both polling and watchdog modes.
    Handles file rotation and truncation robustly.
    """

    def __init__(self, filepath, use_watchdog=True, poll_interval=0.1):
        self.filepath = Path(filepath).absolute()
        self.use_watchdog = use_watchdog
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()

    def stop(self):
        """Signals the tailer to stop reading."""
        self._stop_event.set()

    def tail(self):
        """
        Generator that yields lines from the file.
        Stops when self.stop() is called.
        """
        if self.use_watchdog:
            yield from self._tail_watchdog()
        else:
            yield from self._tail_poll()

    def _tail_poll(self):
        f = None
        last_inode = None
        is_first_open = True

        while not self._stop_event.is_set():
            if f is None:
                try:
                    f = open(self.filepath, "r", encoding="utf-8")
                    if is_first_open:
                        f.seek(0, os.SEEK_END)
                        is_first_open = False
                    # On rotation/truncation we read from the beginning
                    last_inode = os.stat(self.filepath).st_ino
                except FileNotFoundError:
                    time.sleep(self.poll_interval)
                    continue

            try:
                stat = os.stat(self.filepath)
            except FileNotFoundError:
                f.close()
                f = None
                continue

            # Check for truncation or rotation (different inode)
            if stat.st_ino != last_inode or stat.st_size < f.tell():
                f.close()
                f = None
                continue

            line = f.readline()
            if line:
                if not line.endswith("\n"):
                    # Incomplete line, rewind and wait
                    f.seek(f.tell() - len(line))
                    time.sleep(0.01)
                    continue
                yield line.rstrip("\n")
            else:
                time.sleep(self.poll_interval)

        if f is not None:
            f.close()

    def _tail_watchdog(self):
        event_queue = queue.Queue()
        event_handler = _LogEventHandler(self.filepath, event_queue)
        observer = Observer()
        # Watchdog needs an existing directory
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        observer.schedule(event_handler, str(self.filepath.parent), recursive=False)
        observer.start()

        f = None
        last_inode = None
        is_first_open = True

        try:
            while not self._stop_event.is_set():
                if f is None:
                    try:
                        f = open(self.filepath, "r", encoding="utf-8")
                        if is_first_open:
                            f.seek(0, os.SEEK_END)
                            is_first_open = False
                        last_inode = os.stat(self.filepath).st_ino
                    except FileNotFoundError:
                        try:
                            event_queue.get(timeout=self.poll_interval)
                        except queue.Empty:
                            pass
                        continue

                try:
                    stat = os.stat(self.filepath)
                    if stat.st_ino != last_inode or stat.st_size < f.tell():
                        f.close()
                        f = None
                        continue
                except FileNotFoundError:
                    f.close()
                    f = None
                    continue

                line = f.readline()
                if line:
                    if not line.endswith("\n"):
                        f.seek(f.tell() - len(line))
                        time.sleep(0.01)
                        continue
                    yield line.rstrip("\n")
                else:
                    try:
                        event_queue.get(timeout=self.poll_interval)
                    except queue.Empty:
                        pass
        finally:
            observer.stop()
            observer.join(timeout=1.0)
            if f is not None:
                f.close()

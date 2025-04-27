"""
progress_bar.py
---------------
Implements a CLI progress bar for visual feedback during long-running operations in News Intelligence Scout.
"""

import sys
import threading
import time

class ProgressBar:
    def __init__(self, message, total=None, skipped=0):
        self.spinner_cycle = ['|', '/', '-', '\\']
        self.idx = 0
        self.total = total
        self.count = 0
        self.skipped = skipped
        self.message = message
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def update(self, count=None, total=None, skipped=None):
        with self._lock:
            if count is not None:
                self.count = count
            if total is not None:
                self.total = total
            if skipped is not None:
                self.skipped = skipped

    def stop(self):
        self._stop_event.set()

    def run(self):
        while not self._stop_event.is_set():
            with self._lock:
                percent = int((self.count / (self.total or 1)) * 100) if self.total else 0
                spinner = self.spinner_cycle[self.idx % len(self.spinner_cycle)]
                bar = f"[{'#' * (percent // 5):<20}] {percent:3d}% ({self.count}/{self.total if self.total else '?'}) (skipped: {self.skipped})"
                sys.stdout.write(f"\r{bar}  {self.message}... {spinner}")
                sys.stdout.flush()
                self.idx += 1
            time.sleep(0.2)


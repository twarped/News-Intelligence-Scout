"""
simple_spinner.py
-----------------
Implements a simple CLI spinner for indicating activity or waiting in News Intelligence Scout.
"""

import sys
import threading
import time

class SimpleSpinner:
    def __init__(self, message):
        self.spinner_cycle = ['|', '/', '-', '\\']
        self.idx = 0
        self.message = message
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def stop(self):
        self._stop_event.set()

    def run(self):
        while not self._stop_event.is_set():
            with self._lock:
                spinner = self.spinner_cycle[self.idx % len(self.spinner_cycle)]
                sys.stdout.write(f"\r{self.message}... {spinner}")
                sys.stdout.flush()
                self.idx += 1
            time.sleep(0.2)

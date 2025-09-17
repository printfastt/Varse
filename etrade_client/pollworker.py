# poll_worker.py
from PyQt6.QtCore import QObject, pyqtSignal
import time, random

class PollWorker(QObject):
    dataReady: pyqtSignal = pyqtSignal(object)   # emits parsed payload from fetch_fn
    error: pyqtSignal = pyqtSignal(str)
    finished:pyqtSignal = pyqtSignal()

    def __init__(self, fetch_fn, interval=5.0, jitter=0.3):
        super().__init__()
        self.fetch_fn = fetch_fn
        self.interval = float(interval)
        self.jitter = float(jitter)
        self._running = False

    def start(self):
        self._running = True
        self._run()

    def stop(self):
        self._running = False

    def _run(self):
        backoff = 1.0
        while self._running:
            try:
                payload = self.fetch_fn()      # API call
                self.dataReady.emit(payload)   # hand results back to the GUI thread
                backoff = 1.0
            except Exception as e:
                self.error.emit(str(e))
                time.sleep(min(60.0, backoff))
                backoff *= 2.0
            base = self.interval
            time.sleep(max(0.05, base + random.uniform(-base*0.3, base*0.3)))
        self.finished.emit()


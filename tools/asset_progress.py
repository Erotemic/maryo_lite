"""Small terminal progress reporter for Mary-O Lite's first-run asset build.

Progress counts *output assets*, not arbitrary rendering loops. A background
heartbeat reports the last active frame if an expensive painter blocks for
several seconds. No third-party progress bar dependency is required.
"""
from __future__ import annotations

import sys
import threading
import time
from typing import TextIO


def _elapsed(seconds: float) -> str:
    minutes, remainder = divmod(int(max(0, seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f'{hours:d}:{minutes:02d}:{remainder:02d}'
    return f'{minutes:d}:{remainder:02d}'


class AssetProgress:
    """Count built and reused assets with bounded, flushed terminal updates.

    ``stage`` and ``working`` announce what a long-running painter is doing.
    ``advance`` is called once per output (or with ``count`` for a cached
    family). The worker heartbeat never performs any rendering itself.
    """

    def __init__(self, total: int, *, stream: TextIO | None = None,
                 report_seconds: float = 2.0, heartbeat_seconds: float = 6.0):
        if total < 0:
            raise ValueError('progress total cannot be negative')
        self.total = total
        self.stream = stream if stream is not None else sys.stdout
        self.report_seconds = report_seconds
        self.heartbeat_seconds = heartbeat_seconds
        self.completed = 0
        self.built = 0
        self.cached = 0
        self.stage_name = 'Preparing assets'
        self.item = ''
        self._active = False
        self._start = time.monotonic()
        self._last_report = self._start
        self._last_count = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._watcher: threading.Thread | None = None
        self._closed = False

    def __enter__(self) -> AssetProgress:
        self._start = time.monotonic()
        self._last_report = self._start
        self._print(f'Preparing {self.total} generated assets; '
                    'cached files will be reused.')
        if self.heartbeat_seconds > 0:
            self._watcher = threading.Thread(target=self._heartbeat,
                                             daemon=True, name='asset-progress')
            self._watcher.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self._stop.set()
        if self._watcher is not None:
            self._watcher.join(timeout=1.0)
        with self._lock:
            self._closed = True
            if exc_type is not None:
                detail = f' ({self.stage_name}: {self.item})' if self.item else f' ({self.stage_name})'
                result = 'Interrupted' if exc_type is KeyboardInterrupt else 'FAILED'
                self._print(f'{result} at {self.completed}/{self.total}{detail}; '
                            'already generated frames can be reused on retry.')
            else:
                if self.completed != self.total:
                    raise RuntimeError(f'Asset progress mismatch: {self.completed}/{self.total}')
                self._print(f'Complete: {self.completed}/{self.total} (100%) in '
                            f'{_elapsed(time.monotonic() - self._start)}; '
                            f'built {self.built}, reused {self.cached}.')
        return False

    def _print(self, message: str) -> None:
        print('[assets] ' + message, file=self.stream, flush=True)
        self._last_report = time.monotonic()
        self._last_count = self.completed

    def _status(self, *, waiting: bool = False) -> str:
        percent = int(100 * self.completed / self.total) if self.total else 100
        name = self.stage_name + (f' / {self.item}' if self.item else '')
        prefix = 'still painting' if waiting else 'progress'
        return (f'{prefix}: {self.completed}/{self.total} ({percent}%) | {name} | '
                f'elapsed {_elapsed(time.monotonic() - self._start)} | '
                f'built {self.built}, reused {self.cached}')

    def stage(self, name: str) -> None:
        with self._lock:
            self.stage_name = name
            self.item = ''
            self._active = False
            self._print(self._status())

    def working(self, item: str) -> None:
        with self._lock:
            self.item = item
            self._active = True

    def advance(self, count: int = 1, *, cached: bool = False,
                item: str | None = None) -> None:
        if count < 0:
            raise ValueError('cannot advance progress backwards')
        with self._lock:
            self.completed += count
            if self.completed > self.total:
                raise ValueError(f'Asset progress overflow: {self.completed}/{self.total}')
            if cached:
                self.cached += count
            else:
                self.built += count
            if item is not None:
                self.item = item
            self._active = False
            now = time.monotonic()
            threshold = max(1, self.total // 20)
            if (self.completed == self.total or
                self.completed - self._last_count >= threshold or
                now - self._last_report >= self.report_seconds):
                self._print(self._status())

    def _heartbeat(self) -> None:
        interval = min(0.5, self.heartbeat_seconds)
        while not self._stop.wait(interval):
            with self._lock:
                if (not self._closed and self._active and
                    time.monotonic() - self._last_report >= self.heartbeat_seconds):
                    self._print(self._status(waiting=True))

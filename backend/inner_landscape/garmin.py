"""Ephemeral, local heart-rate pacing observations; never an emotion classifier."""
from __future__ import annotations

import secrets
import statistics
import threading
import time
from collections import deque
from typing import Callable


class HeartRateMonitor:
    BASELINE_SECONDS = 30
    MIN_SAMPLES = 15
    STALE_SECONDS = 10
    EXPIRE_SECONDS = 30
    RISE_SECONDS = 5

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self.clock = clock
        self.lock = threading.RLock()
        self.clear()

    def clear(self):
        with self.lock:
            self.sid = self.token = None
            self.last = None
            self.started = self.clock()
            self.reset_window()

    def reset_window(self):
        self.samples = deque(maxlen=180)
        self.baseline = self.bpm = None
        self.rise_since = self.recovery_since = None
        self.rise_count = 0
        self.elevated = False
        self.window_start = None

    def expire(self):
        now = self.clock()
        if self.sid and now - (self.last if self.last is not None else self.started) >= self.EXPIRE_SECONDS:
            self.clear()
        elif self.last is not None and now - self.last >= self.STALE_SECONDS:
            self.reset_window()

    def reconcile(self, active_ids: set[str]):
        with self.lock:
            if self.sid not in active_ids:
                self.clear()
            self.expire()

    def start(self, sid: str):
        with self.lock:
            self.expire()
            if self.sid:
                raise ValueError("Heart-rate monitoring is already active; disconnect it first")
            self.clear()
            self.sid, self.token = sid, secrets.token_urlsafe(32)
            return {"token": self.token, "observation": self.view(sid)}

    def authorize(self, sid: str, token: str):
        self.expire()
        if self.sid != sid or not self.token or not secrets.compare_digest(self.token, token):
            raise ValueError("Heart-rate connection ended; connect again")

    def stop(self, sid: str, token: str):
        with self.lock:
            self.authorize(sid, token)
            self.clear()
            return self.view(sid)

    def sample(self, sid: str, token: str, bpm: int):
        with self.lock:
            self.authorize(sid, token)
            if type(bpm) is not int or not 25 <= bpm <= 240:
                raise ValueError("Invalid BPM sample (accepted device range: 25–240)")
            now = self.clock()
            if self.last is not None and now - self.last < 0.25:
                raise ValueError("Heart-rate samples are arriving too quickly")
            self.last = now
            self.bpm = bpm
            if self.window_start is None:
                self.window_start = now
            if self.baseline is None:
                self.samples.append(bpm)
                if now - self.window_start >= self.BASELINE_SECONDS and len(self.samples) >= self.MIN_SAMPLES:
                    self.baseline = float(statistics.median(self.samples))
            else:
                threshold = self.baseline + max(20, self.baseline * 0.25)
                if bpm >= threshold:
                    if self.rise_since is None:
                        self.rise_since = now
                    self.rise_count += 1
                    self.recovery_since = None
                    if now - self.rise_since >= self.RISE_SECONDS and self.rise_count >= 3:
                        self.elevated = True
                else:
                    self.rise_since = None
                    self.rise_count = 0
                    if bpm <= threshold - 5:
                        if self.recovery_since is None:
                            self.recovery_since = now
                        if now - self.recovery_since >= self.RISE_SECONDS:
                            self.elevated = False
                    else:
                        self.recovery_since = None
            return self.view(sid)

    def view(self, sid: str):
        with self.lock:
            self.expire()
            if self.sid != sid:
                return {"status": "disconnected", "bpm": None, "baseline": None, "spike": False}
            age = self.clock() - self.last if self.last is not None else None
            stale = age is not None and age >= self.STALE_SECONDS
            return {
                "status": "stale" if stale else "baseline" if self.baseline is None else "elevated" if self.elevated else "tracking",
                "bpm": self.bpm,
                "baseline": self.baseline,
                "spike": self.elevated and not stale,
                "age_seconds": round(age, 1) if age is not None else None,
                "baseline_seconds": round(self.clock() - self.window_start, 1) if self.window_start is not None else 0,
                "baseline_samples": len(self.samples),
                "threshold_bpm": self.baseline + max(20, self.baseline * 0.25) if self.baseline is not None else None,
                "cue": "Sustained heart-rate rise. Offer a pause or check in; ask the participant what they need." if self.elevated and not stale else None,
            }

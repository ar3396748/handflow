"""Tracks fingertip trajectory over time to detect circular motion gestures."""

from __future__ import annotations

import math
import time
from collections import deque
import cv2


class MotionTracker:
    def __init__(self, max_history: int = 28, min_points: int = 14) -> None:
        self.max_history = max_history
        self.min_points = min_points
        self.history: deque[tuple[float, float, float]] = deque(maxlen=max_history)
        self.last_circle_time: float = 0.0
        self.circle_cooldown_sec: float = 2.0
        self.last_seen_time: float = 0.0
        self.current_progress_deg: float = 0.0

    def clear(self) -> None:
        self.history.clear()
        self.current_progress_deg = 0.0

    def is_active_motion(self) -> bool:
        """True when actively drawing a circle; suppresses static gestures mid-stroke."""
        return bool(self.current_progress_deg >= 100.0 and len(self.history) >= 8)

    def update(
        self, index_tip_lm, is_index_extended: bool, now: float | None = None
    ) -> tuple[bool, float, dict]:
        if now is None:
            now = time.monotonic()

        if index_tip_lm is None or not is_index_extended:
            if now - self.last_seen_time > 0.40:
                self.history.clear()
                self.current_progress_deg = 0.0
            return False, 0.0, {}

        self.last_seen_time = now
        self.history.append((index_tip_lm.x, index_tip_lm.y, now))

        if now - self.last_circle_time < self.circle_cooldown_sec:
            self.current_progress_deg = 0.0
            return False, 0.0, {}

        if len(self.history) < self.min_points:
            self.current_progress_deg = 0.0
            return False, 0.0, {}

        n = len(self.history)
        cx = sum(p[0] for p in self.history) / n
        cy = sum(p[1] for p in self.history) / n

        radii = [math.hypot(p[0] - cx, p[1] - cy) for p in self.history]
        mean_r = sum(radii) / n
        if mean_r < 0.035 or mean_r > 0.35:
            self.current_progress_deg = 0.0
            return False, 0.0, {"cx": cx, "cy": cy, "mean_r": mean_r}

        angles = [math.atan2(p[1] - cy, p[0] - cx) for p in self.history]
        total_angle = 0.0
        for i in range(len(angles) - 1):
            diff = angles[i + 1] - angles[i]
            while diff > math.pi:
                diff -= 2 * math.pi
            while diff < -math.pi:
                diff += 2 * math.pi
            total_angle += diff

        total_deg = math.degrees(abs(total_angle))
        self.current_progress_deg = min(360.0, total_deg)

        is_circle = total_deg >= 300.0
        if is_circle:
            self.last_circle_time = now
            self.history.clear()
            self.current_progress_deg = 0.0

        metrics = {
            "cx": cx,
            "cy": cy,
            "mean_r": mean_r,
            "total_deg": total_deg,
            "num_points": n,
        }
        return is_circle, self.current_progress_deg, metrics

    def draw_trail(self, frame) -> None:
        if len(self.history) < 2:
            return

        h, w = frame.shape[:2]
        pts = [(int(p[0] * w), int(p[1] * h)) for p in self.history]

        for i in range(1, len(pts)):
            alpha = i / len(pts)
            thickness = max(1, int(1 + alpha * 3))
            color = (int(255 * (1 - alpha)), int(220 * alpha + 35), 255)
            cv2.line(frame, pts[i - 1], pts[i], color, thickness, cv2.LINE_AA)

        head = pts[-1]
        cv2.circle(frame, head, 6, (0, 255, 255), cv2.FILLED, cv2.LINE_AA)
        cv2.circle(frame, head, 8, (0, 165, 255), 1, cv2.LINE_AA)

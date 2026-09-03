"""
Unified camera stream wrapper for webcam and DroidCam inputs.

For network MJPEG streams (droidcam_ip), OpenCV's internal queue buffers frames,
causing several seconds of lag. A background daemon thread continuously drains
the queue so read() always retrieves the latest frame.
"""

from __future__ import annotations

import sys
import threading
import time

import cv2

import config


class CameraStream:
    """Unified capture source supporting USB webcam and DroidCam streams."""

    @staticmethod
    def _prompt_droidcam_url() -> str:
        default_url = config.DROIDCAM_URL
        default_ip = "192.168.7.246"
        if "://" in default_url:
            try:
                netloc = default_url.split("://")[1].split("/")[0]
                default_ip = netloc.split(":")[0]
            except Exception:
                pass

        try:
            user_input = input(f"Enter DroidCam IP address [{default_ip}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            sys.exit(0)

        if not user_input:
            url = default_url
        elif user_input.startswith("http://") or user_input.startswith("https://"):
            url = user_input if user_input.endswith("/video") else user_input.rstrip("/") + "/video"
        elif ":" in user_input:
            host, port = user_input.split(":", 1)
            url = f"http://{host.strip()}:{port.strip()}/video"
        else:
            url = f"http://{user_input}:4747/video"

        config.DROIDCAM_URL = url
        print(f"Connecting to DroidCam stream at {url} ...")
        return url

    def __init__(self, source: str | int | None = None) -> None:
        mode = config.CAMERA_MODE

        if source is not None:
            pass
        elif mode in ("webcam", "droidcam_usb"):
            source = config.WEBCAM_INDEX
        elif mode == "droidcam_ip":
            source = self._prompt_droidcam_url()
        else:
            raise ValueError(
                f"Unknown CAMERA_MODE '{mode}' in config.py. "
                "Valid options: 'webcam', 'droidcam_usb', 'droidcam_ip'."
            )

        self._cap = cv2.VideoCapture(source)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

        if not self._cap.isOpened():
            raise RuntimeError(
                f"Could not open camera source: {source!r}\n"
                "  Webcam / DroidCam USB: check that WEBCAM_INDEX is correct.\n"
                "  DroidCam IP: confirm your phone IP in DROIDCAM_URL and that\n"
                "               the DroidCam app is running and on the same Wi-Fi."
            )

        self._latest_frame = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        if mode == "droidcam_ip":
            self._reader_thread = threading.Thread(
                target=self._background_reader,
                name="CameraStreamReader",
                daemon=True,
            )
            self._reader_thread.start()
        else:
            self._reader_thread = None

    def _background_reader(self) -> None:
        """Continuously grab and cache the latest frame from the network stream."""
        while not self._stop_event.is_set():
            grabbed = self._cap.grab()
            if grabbed:
                ret, frame = self._cap.retrieve()
                if ret:
                    with self._lock:
                        self._latest_frame = frame
            else:
                time.sleep(0.01)

    def read(self) -> tuple[bool, object]:
        """Return (success, frame) as a BGR numpy array."""
        if self._reader_thread is not None:
            with self._lock:
                if self._latest_frame is None:
                    return False, None
                return True, self._latest_frame.copy()
        return self._cap.read()

    def release(self) -> None:
        """Stop background worker and release capture device."""
        self._stop_event.set()
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=2.0)
        self._cap.release()


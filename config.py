from __future__ import annotations

import os
from functools import partial

from actions import (
    take_screenshot,
    show_desktop,
    toggle_mute,
    open_browser,
    media_play_pause,
    open_calculator,
    open_notepad,
    open_file_explorer,
    open_task_manager,
    volume_up,
    volume_down,
    open_settings,
    lock_workstation,
    switch_window,
    open_claude_app,
    open_this_pc,
)

# Camera mode: "webcam", "droidcam_usb", or "droidcam_ip"
CAMERA_MODE: str = "droidcam_ip"
WEBCAM_INDEX: int = 1
DROIDCAM_URL: str = "http://192.168.7.246:4747/video"

FRAME_WIDTH: int = 640
FRAME_HEIGHT: int = 480

MAX_NUM_HANDS: int = 2
DETECTION_CONFIDENCE: float = 0.70
TRACKING_CONFIDENCE: float = 0.60

BUFFER_SIZE: int = 8
BUFFER_THRESHOLD: int = 6
MIN_NEUTRAL_FRAMES: int = 4
ACTION_COOLDOWN_SEC: float = 1.5

PROFILE_PATH: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_profile.json")
SCREENSHOT_FOLDER: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")

GESTURE_ACTION_MAP: dict = {
    "thumbs_up": partial(take_screenshot, SCREENSHOT_FOLDER),
    "thumbs_down": show_desktop,
    "fist": toggle_mute,
    "open_palm": open_browser,
    "index_point": media_play_pause,
    "two_fingers": open_calculator,
    "three_fingers": open_notepad,
    "four_fingers": open_file_explorer,
    "rock_sign": open_task_manager,
    "crossed_fingers": volume_up,
    "l_sign": volume_down,
    "ok_sign": open_settings,
    "back_of_hand": switch_window,
    "double_fist": lock_workstation,
    "double_open_palm": open_claude_app,
    "triangle": open_this_pc,
}

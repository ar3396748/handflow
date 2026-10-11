<p align="center">
  <h1 align="center">HandFlow</h1>
  <p align="center">
    Real-time hand gesture recognition system that maps 16 distinct gestures to Windows desktop automation actions.
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/platform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/MediaPipe-0.10+-00897B?style=flat-square&logo=google&logoColor=white" alt="MediaPipe">
  <img src="https://img.shields.io/badge/OpenCV-4.8+-5C3EE8?style=flat-square&logo=opencv&logoColor=white" alt="OpenCV">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License">
</p>

---

HandFlow is a real-time, vision-based desktop control application for Windows. It uses your smartphone as a wireless camera via **DroidCam (IP stream)** to detect hand landmarks through Google MediaPipe, classifies 16 static gestures using scale-invariant geometric heuristics, and dispatches OS-level actions — screenshots, volume control, app launching, window management, and more — all without touching the keyboard or mouse.

> [!IMPORTANT]
> **This project currently requires [DroidCam](https://www.dev47apps.com/) as the camera source.** You need the DroidCam app installed on your phone and connected to the same Wi-Fi network as your PC. Native USB webcam support is not included out of the box, but the code in `config.py` and `camera_stream.py` can be easily modified to add webcam support.

---

## Table of Contents:

- [Demo](#demo)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [How It Works (Architecture)](#how-it-works-architecture)
  - [System Data Flow](#system-data-flow)
  - [Core Modules](#core-modules)
  - [Key Design Decisions](#key-design-decisions)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
- [Usage](#usage)
  - [Run the Application](#run-the-application)
  - [Biometric Enrollment](#biometric-enrollment)
  - [Gesture Reference Table](#gesture-reference-table)
- [Testing](#testing)
- [Want to Add Webcam Support?](#want-to-add-webcam-support)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)

---

## Demo:

> [!NOTE]
> **[Insert screenshot or GIF of the gesture control HUD in action here]**
>
> Capture a screen recording showing the live telemetry panel, gesture detection labels, and action dispatch feedback overlay.

---

## Features:

- **16 distinct gestures** — 13 single-hand + 3 dual-hand static poses, each mapped to a Windows automation action
- **Edge-triggered dispatch** — temporal majority voting buffer (6/8 frame agreement) eliminates spurious activations
- **Live telemetry HUD** — on-screen debug panel showing finger states, orientation, buffer stability, dispatch status, and cooldown timers
- **Hysteresis thumb detection** — Schmitt trigger logic prevents rapid oscillation at gesture decision boundaries
- **Scale-invariant classification** — all landmark measurements normalized by palm geometry, robust to camera distance
- **DroidCam IP stream** — uses your smartphone as a wireless camera via DroidCam with zero-latency background buffer draining (webcam support can be added by modifying `config.py`)
- **Biometric hand enrollment** — 75-frame profile capture with Z-score outlier filtering for user-specific hand signature storage
- **Cooldown + neutral guard** — 1.5s cooldown AND 4 consecutive neutral frames required before re-arming, preventing double triggers
- **Graceful fallbacks** — browser and app launchers try multiple executable paths before falling back to web URLs
- **UAC-aware elevation** — Task Manager launch uses Win32 `ShellExecuteW` with `runas` verb to handle elevation cleanly

---

## Tech Stack

| Layer | Technology | Purpose |
|:---|:---|:---|
| Hand Tracking | [MediaPipe Hands](https://google.github.io/mediapipe/) ≥ 0.10.0 | 21-point hand landmark estimation |
| Computer Vision | [OpenCV](https://opencv.org/) ≥ 4.8.0 | Camera capture, frame processing, HUD rendering |
| Desktop Automation | [PyAutoGUI](https://pyautogui.readthedocs.io/) ≥ 0.9.54 | Keyboard shortcuts, screenshots, media keys |
| Audio Control | [Pycaw](https://github.com/AndreMiras/pycaw) ≥ 20230326 | Windows Core Audio COM API (mute/volume) |
| COM Interop | [comtypes](https://github.com/enthought/comtypes) ≥ 1.2.0 | COM interface binding for audio endpoints |
| Numerical | [NumPy](https://numpy.org/) ≥ 1.24.0 | Array operations (MediaPipe dependency) |
| Win32 API | `ctypes` (stdlib) | `LockWorkStation`, `ShellExecuteW` system calls |
| Runtime | Python 3.11+ | Type hints with `X \| Y` union syntax |

---

## Project Structure:

```
HandFlow/
├── main.py                 # Application entry point — event loop, state machine, HUD renderer
├── config.py               # Single source of truth: camera, thresholds, gesture→action map
├── gesture_detector.py     # MediaPipe pipeline + 16-gesture geometric classifier (423 lines)
├── camera_stream.py        # Threaded camera wrapper — DroidCam IP stream with buffer draining
├── actions.py              # 16 Windows automation functions (screenshot, mute, launch, etc.)
├── hand_signature.py       # 13D scale-invariant ratio extraction + Z-score outlier filtering
├── enrollment.py           # Biometric hand profile capture (75 frames → filtered → JSON)
├── motion_tracker.py       # Fingertip trajectory tracking + circular gesture detection
├── hand_profile.json       # Serialized 13D biometric reference vector (auto-generated)
├── requirements.txt        # Python package dependencies
├── setup_instructions.md   # Environment setup guide + gesture reference
├── README.md               # This file
├── LICENSE                  # MIT License
├── .gitignore              # Git ignore rules (venv, __pycache__, biometric data, etc.)
├── screenshots/            # Output directory for thumbs-up screenshot action
│   └── screenshot_*.png    # Timestamped captures
└── venv/                   # Python virtual environment (not tracked)
```

---

## How It Works (Architecture)

### System Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Camera Source                            │
│              DroidCam App (IP / MJPEG Stream)               │
│         Phone + PC on same Wi-Fi network required           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              CameraStream  (camera_stream.py)               │
│   • Daemon thread continuously drains MJPEG buffer          │
│   • Thread-safe latest-frame caching via Lock               │
│   • Connects to DroidCam IP endpoint for live video         │
└──────────────────────────┬──────────────────────────────────┘
                           │ BGR Frame
                           ▼
┌─────────────────────────────────────────────────────────────┐
│            GestureDetector  (gesture_detector.py)            │
│   • MediaPipe Hands → 21 landmarks per hand (up to 2)      │
│   • Scale-invariant finger extension analysis               │
│   • Thumb hysteresis (Schmitt trigger dead-zone)            │
│   • Two-hand priority → single-hand hierarchical classify   │
└──────────────────────────┬──────────────────────────────────┘
                           │ Raw Gesture String (or None)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Main Loop  (main.py)                        │
│   • Rolling deque buffer (8 frames)                         │
│   • Majority vote: ≥6/8 agreement → STABLE                 │
│   • Edge-triggered dispatch (fires once on rising edge)     │
│   • Re-arm guard: cooldown (1.5s) + neutral frames (≥4)    │
│   • Telemetry HUD overlay rendering                         │
└──────────────────────────┬──────────────────────────────────┘
                           │ Stable Gesture Confirmed
                           ▼
┌─────────────────────────────────────────────────────────────┐
│            Actions Dispatcher  (actions.py)                  │
│   • Win32 API: LockWorkStation, ShellExecuteW (runas)       │
│   • COM: Pycaw IAudioEndpointVolume (mute/volume)           │
│   • PyAutoGUI: hotkeys, media keys, screenshots             │
│   • Subprocess: calc, notepad, explorer, chrome, claude     │
└─────────────────────────────────────────────────────────────┘
```

### Core Modules

| Module | Responsibility |
|:---|:---|
| **`config.py`** | Centralizes all tunable parameters (camera mode, MediaPipe confidence thresholds, buffer sizes, cooldowns) and constructs the `GESTURE_ACTION_MAP` dictionary binding gesture strings to callable functions via `functools.partial`. |
| **`gesture_detector.py`** | Runs the MediaPipe Hands pipeline, extracts 21 landmarks, computes scale-invariant geometric features (finger extension ratios, inter-finger distances, palm orientation), and classifies into one of 16 gesture names using a priority-ordered heuristic chain. Two-hand gestures (triangle, double fist, double palm) are evaluated first. |
| **`camera_stream.py`** | Wraps `cv2.VideoCapture` with a background daemon thread that continuously `grab()`s frames from the DroidCam IP stream, eliminating multi-second MJPEG buffer lag. The code structure supports adding webcam or DroidCam USB sources by modifying `config.py`. |
| **`main.py`** | Orchestrates the real-time loop: captures frames → detects gestures → feeds a rolling deque → majority-votes for temporal stability → dispatches actions on the rising edge → enforces cooldown + neutral-hand re-arming. Also renders the telemetry HUD and action feedback banners. |
| **`actions.py`** | 16 pure functions, each performing a single Windows automation task. Includes multi-path executable discovery with web fallback for Chrome and Claude, defensive COM binding across pycaw versions, and UAC-aware elevation for Task Manager. |
| **`hand_signature.py`** | Extracts a 13-dimensional scale-invariant ratio vector from hand landmarks (5 finger lengths, palm aspect ratio, 3 knuckle spans, 4 fingertip spreads — all normalized by palm geometry). Includes Z-score outlier filtering and JSON serialization for biometric enrollment. |
| **`enrollment.py`** | Interactive enrollment routine that collects 75 frames of open-palm landmarks, runs Z-score filtering to discard tracking glitches, computes mean signature, and saves the reference profile to `hand_profile.json`. |
| **`motion_tracker.py`** | Tracks index fingertip trajectories in a rolling deque, computes cumulative phase-unwrapped rotation angles, and detects completed circular air-drawing gestures. Includes active stroke gating to suppress static gesture misclassification during motion. |

### Key Design Decisions

| Decision | Rationale |
|:---|:---|
| **Temporal majority voting** (not raw per-frame) | Single-frame classification is noisy. Requiring 6/8 frame agreement filters tracking jitter without adding perceptible latency. |
| **Edge-triggered dispatch** (not level-triggered) | Actions fire exactly once on the "rising edge" of stabilization, not continuously while a gesture is held. This prevents screenshot floods or repeated app launches. |
| **Hysteresis on thumb state** | The thumb curl/extend boundary is geometrically ambiguous. A Schmitt trigger with separate extend (0.46) and curl (0.35) thresholds eliminates rapid state toggling. |
| **Neutral-frame re-arming guard** | Cooldown alone isn't sufficient — the user might still be holding the gesture when cooldown expires. Requiring 4 consecutive neutral (no-gesture) frames ensures intentional release before re-arming. |
| **Background buffer draining for DroidCam IP** | DroidCam's MJPEG feed accumulates frames in OpenCV's internal buffer, causing multi-second lag. A daemon thread continuously `grab()`s to drain the buffer, ensuring `read()` always returns the latest frame. |
| **Scale-invariant geometric heuristics** (not ML) | Avoids the need for training data collection and model deployment. Landmark ratio normalization makes classification robust across hand sizes and camera distances. |

---

## Getting Started

### Prerequisites

| Requirement | Version | Notes |
|:---|:---|:---|
| **Python** | 3.11+ | Required for `X \| Y` union type syntax |
| **OS** | Windows 10/11 | Win32 API calls (`ctypes.windll`) are Windows-only |
| **Camera** | [DroidCam](https://www.dev47apps.com/) app on phone | Phone and PC must be on the same Wi-Fi network |
| **pip** | Latest | For dependency installation |

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/ar3396748/HandFlow.git
   cd HandFlow
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv venv
   ```

   **CMD:**
   ```cmd
   venv\Scripts\activate.bat
   ```

   **PowerShell:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up DroidCam**

   1. Install the **DroidCam** app on your phone — [Android](https://play.google.com/store/apps/details?id=com.dev47apps.droidcam) / [iOS](https://apps.apple.com/app/droidcam-webcam-obs-camera/id1510258102)
   2. Connect your phone and PC to the **same Wi-Fi network**
   3. Open DroidCam on your phone — it will display an **IP address** (e.g., `192.168.1.100`)
   4. Open [`config.py`](config.py) and update the `DROIDCAM_URL` with your phone's IP:
      ```python
      DROIDCAM_URL: str = "http://<YOUR_PHONE_IP>:4747/video"
      ```

### Configuration

All runtime parameters are in [`config.py`](config.py). Key settings to review:

| Variable | Default | Description |
|:---|:---|:---|
| `CAMERA_MODE` | `"droidcam_ip"` | Camera source — currently only `"droidcam_ip"` is supported. Change to `"webcam"` or `"droidcam_usb"` if you add webcam support |
| `DROIDCAM_URL` | `"http://192.168.7.246:4747/video"` | **⚠️ Update this to your phone's IP.** Open DroidCam on your phone to see the IP address |
| `FRAME_WIDTH` / `FRAME_HEIGHT` | `640` / `480` | Capture resolution |
| `DETECTION_CONFIDENCE` | `0.70` | MediaPipe hand detection threshold |
| `TRACKING_CONFIDENCE` | `0.60` | MediaPipe landmark tracking threshold |
| `BUFFER_SIZE` | `8` | Rolling gesture buffer capacity (frames) |
| `BUFFER_THRESHOLD` | `6` | Minimum matching frames for stable gesture |
| `ACTION_COOLDOWN_SEC` | `1.5` | Seconds before re-arming after action dispatch |
| `MIN_NEUTRAL_FRAMES` | `4` | Consecutive neutral frames required to re-arm |

---

## Usage

### Run the Application

```bash
python main.py
```

**Expected output:**

```
=======================================================
  Gesture Control - Armed and Ready
=======================================================
Loaded 16 gestures:
  * thumbs_up          -> take_screenshot
  * thumbs_down        -> show_desktop
  * fist               -> toggle_mute
  * open_palm          -> open_browser
  * index_point        -> media_play_pause
  * two_fingers        -> open_calculator
  * three_fingers      -> open_notepad
  * four_fingers       -> open_file_explorer
  * rock_sign          -> open_task_manager
  * crossed_fingers    -> volume_up
  * l_sign             -> volume_down
  * ok_sign            -> open_settings
  * back_of_hand       -> switch_window
  * double_fist        -> lock_workstation
  * double_open_palm   -> open_claude_app
  * triangle           -> open_this_pc

Press 'q' in the window to exit.
```

A camera window opens with the live telemetry HUD. Hold any mapped gesture steady for ~0.5s to trigger its action.

### Biometric Enrollment

To capture your personal hand profile (used for hand signature verification):

```bash
python main.py --enroll
```

This opens the camera, prompts you to hold an open palm, captures 75 sample frames, filters outliers via Z-score analysis, and saves the averaged 13-dimensional signature to `hand_profile.json`.

### Gesture Reference Table

| # | Gesture | Key | Type | Windows Action |
|:---:|:---|:---|:---:|:---|
| 1 | 👍 Thumbs Up | `thumbs_up` | 1-Hand | Screenshot → `screenshots/` |
| 2 | 👎 Thumbs Down | `thumbs_down` | 1-Hand | Show Desktop (`Win+D`) |
| 3 | ✊ Fist | `fist` | 1-Hand | Toggle Mute/Unmute |
| 4 | ✋ Open Palm | `open_palm` | 1-Hand | Launch Chrome |
| 5 | ☝️ Index Point | `index_point` | 1-Hand | Media Play/Pause |
| 6 | ✌️ Peace / Two Fingers | `two_fingers` | 1-Hand | Open Calculator |
| 7 | 🤟 Three Fingers | `three_fingers` | 1-Hand | Open Notepad |
| 8 | 🖖 Four Fingers | `four_fingers` | 1-Hand | Open File Explorer |
| 9 | 🤘 Rock / Horns | `rock_sign` | 1-Hand | Open Task Manager (UAC) |
| 10 | 🤞 Crossed Fingers | `crossed_fingers` | 1-Hand | Volume Up (+10%) |
| 11 | 🔫 L-Sign / Gun | `l_sign` | 1-Hand | Volume Down (−10%) |
| 12 | 👌 OK Sign | `ok_sign` | 1-Hand | Open Windows Settings |
| 13 | 🤚 Back of Hand | `back_of_hand` | 1-Hand | Switch Window (`Alt+Tab`) |
| 14 | 🥊 Double Fists | `double_fist` | 2-Hand | Lock Workstation |
| 15 | 👐 Double Open Palms | `double_open_palm` | 2-Hand | Launch Claude App |
| 16 | 🔺 Triangle | `triangle` | 2-Hand | Open "This PC" |

---

## Testing

> [!WARNING]
> This project does not currently include an automated test suite. Manual verification is done by running the application and performing each gesture in front of the camera.

**Manual verification checklist:**

```bash
# 1. Start the app
python main.py

# 2. Verify camera feed appears with telemetry HUD
# 3. Perform each gesture and confirm action dispatches in the terminal log
# 4. Verify cooldown prevents double-triggering
# 5. Verify two-hand gestures (triangle, double fist, double palm)
# 6. Press 'q' to exit cleanly
```

---

## Want to Add Webcam Support?

This project currently only supports **DroidCam IP streams**. However, the codebase is designed to make adding USB webcam support straightforward. Here's what you'd need to change:

1. **In `config.py`** — change the camera mode:
   ```python
   CAMERA_MODE: str = "webcam"       # Change from "droidcam_ip" to "webcam"
   WEBCAM_INDEX: int = 0             # 0 for default camera, 1 for secondary
   ```

2. **In `camera_stream.py`** — the class already has conditional logic for different `CAMERA_MODE` values. Setting `"webcam"` will use `cv2.VideoCapture(WEBCAM_INDEX)` directly without the background thread buffer draining (which is only needed for network streams).

> [!TIP]
> Contributions adding full webcam support are welcome! See the [Contributing](#contributing) section below.

---

## Contributing

Contributions are welcome. To get started:

1. **Fork** the repository
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Commit** with descriptive messages:
   ```bash
   git commit -m "feat: add swipe gesture detection"
   ```
4. **Push** and open a **Pull Request**

Please ensure your code:
- Follows the existing module structure and naming conventions
- Includes docstrings for all public functions
- Works on Windows 10/11 with Python 3.11+

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## Author

- **Name:** Abdullah Abrar
- **GitHub:** [ar3396748](https://github.com/ar3396748)
- **Email:** [ar3396748@gmail.com](mailto:ar3396748@gmail.com)

"""Entry point for real-time gesture recognition with edge-triggered action dispatch."""

from __future__ import annotations

import sys
import time
from collections import Counter, deque
import cv2

import config
from camera_stream import CameraStream
from enrollment import run_enrollment
from gesture_detector import GestureDetector


def get_stable_gesture(
    buffer: deque, threshold: int = config.BUFFER_THRESHOLD
) -> tuple[str | None, int, str]:
    """Evaluate rolling buffer of recent frames for a temporally stable gesture."""
    if len(buffer) < buffer.maxlen:
        return None, 0, "Filling buffer..."

    counts = Counter(buffer)
    most_common_gesture, count = counts.most_common(1)[0]

    if most_common_gesture is not None and count >= threshold:
        return most_common_gesture, count, f"{most_common_gesture} ({count}/{buffer.maxlen}) [STABLE]"
    else:
        top_name = most_common_gesture if most_common_gesture else "neutral"
        return None, count, f"{top_name} ({count}/{buffer.maxlen}) [UNSTABLE]"


def draw_text_with_bg(
    frame,
    text: str,
    pos: tuple[int, int],
    font_scale: float = 0.70,
    thickness: int = 2,
    text_color: tuple[int, int, int] = (255, 255, 255),
    bg_color: tuple[int, int, int] = (20, 20, 20),
    padding: int = 6,
) -> None:
    """Render anti-aliased text with a solid background box."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    x, y = pos

    cv2.rectangle(
        frame,
        (x - padding, y - text_h - padding),
        (x + text_w + padding, y + baseline + padding),
        bg_color,
        cv2.FILLED,
    )
    cv2.putText(frame, text, (x, y), font, font_scale, text_color, thickness, cv2.LINE_AA)


def draw_debug_panel(
    frame,
    debug_info: dict | None,
    buffer_summary: str,
    stable_gesture: str | None,
    armed: bool,
    active_gesture: str | None,
    cooldown_remaining: float,
) -> None:
    """Draw live telemetry in the lower-left corner."""
    h, _ = frame.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.37
    pad = 6

    x0 = 10
    y0 = h - 140
    panel_w = 395
    panel_h = 125

    cv2.rectangle(frame, (x0, y0), (x0 + panel_w, y0 + panel_h), (20, 20, 20), cv2.FILLED)
    cv2.rectangle(frame, (x0, y0), (x0 + panel_w, y0 + panel_h), (70, 70, 70), 1)

    cv2.putText(frame, "LIVE TELEMETRY HUD", (x0 + pad, y0 + 16), font, 0.36, (0, 215, 255), 1, cv2.LINE_AA)

    if debug_info is None:
        cv2.putText(frame, "No hand detected (Neutral)", (x0 + pad, y0 + 38), font, font_scale, (150, 150, 150), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Buffer: {buffer_summary}", (x0 + pad, y0 + 58), font, font_scale, (180, 180, 180), 1, cv2.LINE_AA)
        state_text = "Dispatch: READY" if armed else f"Dispatch: COOLDOWN ({cooldown_remaining:.1f}s)"
        state_color = (0, 255, 120) if armed else (0, 165, 255)
        cv2.putText(frame, state_text, (x0 + pad, y0 + 78), font, font_scale, state_color, 1, cv2.LINE_AA)
        return

    num_hands = debug_info.get("num_hands", 1)

    if num_hands == 2:
        h0_st = debug_info.get("h0_state", "N/A")
        h1_st = debug_info.get("h1_state", "N/A")
        d_wr = debug_info.get("d_wrist", 0.0)
        cv2.putText(frame, f"Hands: 2 | H0: {h0_st} | H1: {h1_st} | Dist:{d_wr:.2f}", (x0 + pad, y0 + 38), font, font_scale, (0, 255, 255), 1, cv2.LINE_AA)

        target_act = debug_info.get("target_action", "None")
        cv2.putText(frame, f"Two-Hand Target: {target_act}", (x0 + pad, y0 + 58), font, font_scale, (100, 255, 100), 1, cv2.LINE_AA)

        two_g_name = debug_info.get("two_hand_gesture", "Two-Hand Pose")
        cv2.putText(frame, f"Mode: {two_g_name}", (x0 + pad, y0 + 78), font, font_scale, (180, 220, 255), 1, cv2.LINE_AA)
    else:
        is_5_ext = "YES" if debug_info.get("five_fingers_ext", False) else "NO"
        orient = debug_info.get("orientation", "palm").upper()
        x_val = debug_info.get("x_diff", 0.0)
        cv2.putText(
            frame,
            f"5-Fingers Ext: {is_5_ext} | Orient: {orient} (X:{x_val:+.2f})",
            (x0 + pad, y0 + 38),
            font,
            font_scale,
            (0, 255, 255) if is_5_ext == "YES" else (220, 220, 220),
            1,
            cv2.LINE_AA,
        )

        target_act = debug_info.get("target_action", "None")
        cv2.putText(frame, f"Target Action: {target_act}", (x0 + pad, y0 + 58), font, font_scale, (100, 255, 100), 1, cv2.LINE_AA)

        t_state = "EXT" if debug_info["fingers"][0] else "CURL"
        t_ratio = debug_info.get("norm_dist_t_idx", 0.0)
        angle = debug_info.get("thumb_angle", 0.0)
        t_str = f"Thumb: {t_state} (R:{t_ratio:.2f}, {angle:.0f}deg) | Fingers: {debug_info['count_up']} Up"
        cv2.putText(frame, t_str, (x0 + pad, y0 + 78), font, font_scale, (180, 220, 255), 1, cv2.LINE_AA)

    buf_color = (0, 255, 255) if "[STABLE]" in buffer_summary else (180, 180, 180)
    cv2.putText(frame, f"Buffer: {buffer_summary}", (x0 + pad, y0 + 98), font, font_scale, buf_color, 1, cv2.LINE_AA)

    if armed:
        state_str = "Dispatch: READY"
        state_color = (0, 255, 100)
    else:
        if active_gesture and stable_gesture == active_gesture:
            state_str = f"Dispatch: ACTIVE ({active_gesture} - release to reset)"
            state_color = (0, 140, 255)
        elif cooldown_remaining > 0.0:
            state_str = f"Dispatch: COOLDOWN ({cooldown_remaining:.1f}s)"
            state_color = (0, 165, 255)
        else:
            state_str = "Dispatch: RESETTING (Awaiting neutral hand)"
            state_color = (0, 200, 255)

    cv2.putText(frame, state_str, (x0 + pad, y0 + 116), font, font_scale, state_color, 1, cv2.LINE_AA)


def main() -> None:
    cam = CameraStream()
    detector = GestureDetector()

    if "--enroll" in sys.argv:
        print("Starting hand signature enrollment...")
        run_enrollment(cam=cam, detector=detector)

    gesture_buffer: deque = deque(maxlen=config.BUFFER_SIZE)
    armed: bool = True
    active_gesture: str | None = None
    last_action_time: float = 0.0
    consecutive_neutral_frames: int = 0

    status_msg: str = ""
    status_until: float = 0.0

    window_name = "Gesture Control"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    print("=" * 55)
    print("  Gesture Control - Armed and Ready")
    print("=" * 55)
    print(f"Loaded {len(config.GESTURE_ACTION_MAP)} gestures:")
    for g, action_fn in config.GESTURE_ACTION_MAP.items():
        fn_name = action_fn.func.__name__ if hasattr(action_fn, "func") else action_fn.__name__
        print(f"  * {g:<18} -> {fn_name}")
    print("\nPress 'q' in the window to exit.\n")

    while True:
        ok, frame = cam.read()
        if not ok or frame is None:
            time.sleep(0.02)
            continue

        now = time.monotonic()
        frame = cv2.flip(frame, 1)

        annotated, raw_gesture, debug_info = detector.process(frame)

        cooldown_elapsed = now - last_action_time
        cooldown_remaining = max(0.0, config.ACTION_COOLDOWN_SEC - cooldown_elapsed)

        gesture_buffer.append(raw_gesture)
        stable_gesture, match_count, buf_summary = get_stable_gesture(gesture_buffer)

        # Edge-triggered gesture action dispatch
        if stable_gesture is not None:
            consecutive_neutral_frames = 0
            if armed and (stable_gesture in config.GESTURE_ACTION_MAP):
                action_func = config.GESTURE_ACTION_MAP[stable_gesture]
                fn_name = action_func.func.__name__ if hasattr(action_func, "func") else action_func.__name__
                result_msg = action_func()
                status_msg = result_msg
                status_until = now + 2.5
                last_action_time = now
                armed = False
                active_gesture = stable_gesture
                print(f"[{time.strftime('%H:%M:%S')}] {stable_gesture:<18} -> {fn_name}() | {result_msg}")
        else:
            consecutive_neutral_frames += 1
            if not armed:
                # Re-arm only after cooldown and consecutive neutral frames to prevent double triggers
                if (cooldown_elapsed >= config.ACTION_COOLDOWN_SEC) and (consecutive_neutral_frames >= config.MIN_NEUTRAL_FRAMES):
                    armed = True
                    active_gesture = None

        h, _ = annotated.shape[:2]

        display_label = stable_gesture if stable_gesture else "-- (Neutral)"
        draw_text_with_bg(annotated, f"Gesture: {display_label}", (10, 32), font_scale=0.72)

        if now < status_until and status_msg:
            is_err = any(w in status_msg.lower() for w in ("failed", "mismatch", "wrong", "error"))
            msg_color = (50, 50, 240) if is_err else (60, 235, 60)
            draw_text_with_bg(annotated, status_msg, (10, 68), font_scale=0.60, text_color=msg_color)

        draw_debug_panel(
            annotated,
            debug_info,
            buf_summary,
            stable_gesture,
            armed,
            active_gesture,
            cooldown_remaining,
        )

        draw_text_with_bg(annotated, "Press 'q' to quit", (10, h - 8), font_scale=0.38, thickness=1, padding=3)

        cv2.imshow(window_name, annotated)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    detector.close()
    cam.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

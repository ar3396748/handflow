"""Interactive hand biometric profile enrollment routine."""

from __future__ import annotations

import time
import cv2

import config
from camera_stream import CameraStream
from gesture_detector import GestureDetector
from hand_signature import extract_hand_signature, filter_outliers_and_average, save_profile


def draw_enrollment_overlay(
    frame,
    progress: float,
    frames_collected: int,
    status_text: str,
    status_color: tuple[int, int, int],
) -> None:
    """Render enrollment progress HUD on the video frame."""
    h, w = frame.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX

    cv2.rectangle(frame, (0, 0), (w, 64), (20, 20, 20), cv2.FILLED)
    cv2.line(frame, (0, 64), (w, 64), (0, 215, 255), 2)
    cv2.putText(
        frame,
        "HAND SIGNATURE ENROLLMENT",
        (15, 28),
        font,
        0.70,
        (0, 215, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        "Hold your Open Palm steady in front of camera for ~3 seconds",
        (15, 50),
        font,
        0.42,
        (220, 220, 220),
        1,
        cv2.LINE_AA,
    )

    card_h = 95
    card_w = 460
    x0 = (w - card_w) // 2
    y0 = h - card_h - 15

    cv2.rectangle(frame, (x0, y0), (x0 + card_w, y0 + card_h), (25, 25, 25), cv2.FILLED)
    cv2.rectangle(frame, (x0, y0), (x0 + card_w, y0 + card_h), (80, 80, 80), 1)

    cv2.putText(frame, status_text, (x0 + 15, y0 + 26), font, 0.48, status_color, 1, cv2.LINE_AA)

    bar_x = x0 + 15
    bar_y = y0 + 40
    bar_w = card_w - 30
    bar_h = 16

    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 50, 50), cv2.FILLED)
    fill_w = int(bar_w * min(1.0, max(0.0, progress)))
    if fill_w > 0:
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), (0, 220, 100), cv2.FILLED)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (180, 180, 180), 1)

    pct_text = f"Collecting: {int(progress * 100)}% ({frames_collected} frames)"
    cv2.putText(frame, pct_text, (bar_x, bar_y + bar_h + 20), font, 0.40, (200, 200, 200), 1, cv2.LINE_AA)
    cv2.putText(frame, "Press 'q' to cancel", (x0 + card_w - 140, bar_y + bar_h + 20), font, 0.38, (140, 140, 140), 1, cv2.LINE_AA)


def run_enrollment(cam: CameraStream | None = None, detector: GestureDetector | None = None) -> bool:
    """Collect sample frames of open palm landmarks, filter outliers, and save profile."""
    owns_cam = False
    if cam is None:
        cam = CameraStream()
        owns_cam = True

    owns_detector = False
    if detector is None:
        detector = GestureDetector()
        owns_detector = True

    window_name = "Hand Enrollment"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    target_frames = 75
    collected_signatures: list[list[float]] = []
    consecutive_steady = 0

    print("\n" + "=" * 55)
    print("  Hand Signature Enrollment Routine")
    print("=" * 55)
    print("Hold an OPEN PALM steady facing the camera (~3 seconds).\n")

    success = False

    while True:
        ok, frame = cam.read()
        if not ok or frame is None:
            time.sleep(0.02)
            continue

        frame = cv2.flip(frame, 1)
        annotated, _, debug_info = detector.process(frame)

        status_text = "Hold Open Palm steady in frame..."
        status_color = (0, 180, 255)

        if debug_info and debug_info.get("num_hands", 0) == 1:
            five_ext = debug_info.get("five_fingers_ext", False)
            orient = debug_info.get("orientation", "")
            lm = debug_info.get("lm", None)

            if five_ext and orient == "palm" and lm is not None:
                sig = extract_hand_signature(lm)
                if sig is not None:
                    collected_signatures.append(sig)
                    consecutive_steady += 1
                    status_text = "Palm detected. Holding steady..."
                    status_color = (0, 255, 100)
            else:
                consecutive_steady = max(0, consecutive_steady - 2)
                status_text = "Please spread all 5 fingers facing camera (Open Palm)"
                status_color = (0, 140, 255)
        else:
            consecutive_steady = max(0, consecutive_steady - 2)
            status_text = "No hand detected. Place one hand in frame."
            status_color = (50, 50, 240)

        progress = len(collected_signatures) / float(target_frames)
        draw_enrollment_overlay(annotated, progress, len(collected_signatures), status_text, status_color)

        cv2.imshow(window_name, annotated)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            print("[Enrollment] Cancelled by user.")
            break

        if len(collected_signatures) >= target_frames:
            ref_vector, inlier_count, total_count = filter_outliers_and_average(
                collected_signatures, z_threshold=2.0
            )
            outliers_discarded = total_count - inlier_count

            meta = {
                "total_frames_sampled": total_count,
                "inlier_frames_used": inlier_count,
                "outliers_discarded": outliers_discarded,
                "z_threshold": 2.0,
            }
            save_ok = save_profile(config.PROFILE_PATH, ref_vector, metadata=meta)

            if save_ok:
                print(f"[Enrollment] Profile saved to {config.PROFILE_PATH} ({inlier_count}/{total_count} inliers).")
                success = True

                h, w = annotated.shape[:2]
                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.rectangle(annotated, (w // 2 - 200, h // 2 - 50), (w // 2 + 200, h // 2 + 50), (20, 20, 20), cv2.FILLED)
                cv2.rectangle(annotated, (w // 2 - 200, h // 2 - 50), (w // 2 + 200, h // 2 + 50), (0, 255, 100), 2)
                cv2.putText(annotated, "ENROLLMENT COMPLETE", (w // 2 - 165, h // 2 - 10), font, 0.70, (0, 255, 100), 2, cv2.LINE_AA)
                cv2.putText(annotated, f"Profile Saved ({inlier_count}/{total_count} inliers)", (w // 2 - 160, h // 2 + 25), font, 0.45, (220, 220, 220), 1, cv2.LINE_AA)
                cv2.imshow(window_name, annotated)
                cv2.waitKey(1800)
            else:
                print("[Enrollment] Error: Could not save profile file.")

            break

    cv2.destroyWindow(window_name)

    if owns_cam:
        cam.release()
    if owns_detector:
        detector.close()

    return success


if __name__ == "__main__":
    run_enrollment()

"""Hand landmark tracking and 16-gesture classification using MediaPipe."""

from __future__ import annotations

import math
import cv2
import mediapipe as mp

import config


class GestureDetector:
    """Classifies single-hand and two-hand static gestures from video frames."""

    FINGER_TIP_IDS = [4, 8, 12, 16, 20]

    def __init__(self) -> None:
        self._mp_hands = mp.solutions.hands
        self._mp_draw = mp.solutions.drawing_utils
        self._mp_styles = mp.solutions.drawing_styles

        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=config.MAX_NUM_HANDS,
            min_detection_confidence=config.DETECTION_CONFIDENCE,
            min_tracking_confidence=config.TRACKING_CONFIDENCE,
        )

        # State hysteresis to avoid thumb boundary flicker
        self._last_thumb_state: bool = False

    def process(self, frame_bgr) -> tuple[object, str | None, dict | None]:
        """Run landmark detection and gesture classification on a single BGR frame."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._hands.process(rgb)
        rgb.flags.writeable = True

        annotated = frame_bgr.copy()
        gesture_name = None
        debug_info = None

        if results.multi_hand_landmarks:
            num_hands = len(results.multi_hand_landmarks)

            for hand_landmarks in results.multi_hand_landmarks:
                self._mp_draw.draw_landmarks(
                    annotated,
                    hand_landmarks,
                    self._mp_hands.HAND_CONNECTIONS,
                    self._mp_styles.get_default_hand_landmarks_style(),
                    self._mp_styles.get_default_hand_connections_style(),
                )

            if num_hands == 2:
                hand0_lm = results.multi_hand_landmarks[0].landmark
                hand1_lm = results.multi_hand_landmarks[1].landmark
                label0 = results.multi_handedness[0].classification[0].label
                label1 = results.multi_handedness[1].classification[0].label

                f_bool0, sig0 = self._fingers_up(hand0_lm, label0)
                f_bool1, sig1 = self._fingers_up(hand1_lm, label1)

                wrist0 = hand0_lm[0]
                wrist1 = hand1_lm[0]
                d_wrist = self._dist(wrist0, wrist1)
                d_idx_tips = self._dist(hand0_lm[8], hand1_lm[8])

                is_triangle, _ = self._check_two_hand_triangle(hand0_lm, hand1_lm)
                if is_triangle:
                    gesture_name = "triangle"
                    debug_info = {
                        "num_hands": 2,
                        "two_hand_gesture": "Triangle",
                        "h0_state": f"Up:{sig0['count_up']}",
                        "h1_state": f"Up:{sig1['count_up']}",
                        "d_wrist": d_wrist,
                        "d_idx_tips": d_idx_tips,
                        "target_action": "This PC",
                        "fingers": f_bool0,
                        "orientation": "Two-Hand",
                        "x_diff": 0.0,
                        "thumb_angle": 0.0,
                        "norm_dist_t_idx": 0.0,
                        "five_fingers_ext": False,
                    }
                    return annotated, gesture_name, debug_info

                is_h0_fist = bool(sig0["count_up"] == 0 and not sig0["fingers_bool"][0])
                is_h1_fist = bool(sig1["count_up"] == 0 and not sig1["fingers_bool"][0])
                if is_h0_fist and is_h1_fist and d_wrist < 0.45:
                    gesture_name = "double_fist"
                    debug_info = {
                        "num_hands": 2,
                        "two_hand_gesture": "Double Fist",
                        "h0_state": "FIST (0 up)",
                        "h1_state": "FIST (0 up)",
                        "d_wrist": d_wrist,
                        "d_idx_tips": d_idx_tips,
                        "target_action": "Lock Workstation",
                        "fingers": f_bool0,
                        "orientation": "Two-Hand",
                        "x_diff": 0.0,
                        "thumb_angle": 0.0,
                        "norm_dist_t_idx": 0.0,
                        "five_fingers_ext": False,
                    }
                    return annotated, gesture_name, debug_info

                is_h0_palm = bool(sig0["count_up"] == 5 and sig0["orientation"] == "palm")
                is_h1_palm = bool(sig1["count_up"] == 5 and sig1["orientation"] == "palm")
                if is_h0_palm and is_h1_palm and d_idx_tips > 0.08 and abs(wrist0.y - wrist1.y) < 0.25:
                    gesture_name = "double_open_palm"
                    debug_info = {
                        "num_hands": 2,
                        "two_hand_gesture": "Double Open Palms",
                        "h0_state": "PALM (5 up)",
                        "h1_state": "PALM (5 up)",
                        "d_wrist": d_wrist,
                        "d_idx_tips": d_idx_tips,
                        "target_action": "Claude App",
                        "fingers": f_bool0,
                        "orientation": "Two-Hand",
                        "x_diff": 0.0,
                        "thumb_angle": 0.0,
                        "norm_dist_t_idx": 0.0,
                        "five_fingers_ext": True,
                    }
                    return annotated, gesture_name, debug_info

                # Fallback to single-hand evaluation on the primary hand
                gesture_name = self._classify_gesture(sig0)
                debug_info = {
                    "num_hands": 2,
                    "two_hand_gesture": "None (Primary Hand)",
                    "h0_state": f"Up:{sig0['count_up']}",
                    "h1_state": f"Up:{sig1['count_up']}",
                    "d_wrist": d_wrist,
                    "d_idx_tips": d_idx_tips,
                    "target_action": gesture_name if gesture_name else "None",
                    "fingers": f_bool0,
                    "orientation": sig0["orientation"],
                    "x_diff": sig0["x_diff"],
                    "thumb_angle": sig0["thumb_index_angle"],
                    "norm_dist_t_idx": sig0["norm_dist_t_idx"],
                    "five_fingers_ext": sig0["five_fingers_ext"],
                    "lm": hand0_lm,
                }
                return annotated, gesture_name, debug_info

            hand_lm = results.multi_hand_landmarks[0]
            handedness = results.multi_handedness[0]
            label = handedness.classification[0].label
            lm_list = hand_lm.landmark

            fingers_bool, signals = self._fingers_up(lm_list, label)
            gesture_name = self._classify_gesture(signals)

            target_action = "None"
            if gesture_name == "open_palm":
                target_action = "Google Chrome"
            elif gesture_name == "back_of_hand":
                target_action = "Alt+Tab Switch Window"
            elif gesture_name in config.GESTURE_ACTION_MAP:
                target_action = gesture_name

            debug_info = {
                "num_hands": 1,
                "two_hand_gesture": "Single Hand Mode",
                "h0_state": f"Up:{signals['count_up']}",
                "h1_state": "N/A",
                "d_wrist": 0.0,
                "d_idx_tips": 0.0,
                "handedness": label,
                "orientation": signals["orientation"],
                "five_fingers_ext": signals["five_fingers_ext"],
                "fingers": fingers_bool,
                "gesture": gesture_name,
                "x_diff": signals["x_diff"],
                "z_diff": signals["z_diff"],
                "thumb_angle": signals["thumb_index_angle"],
                "norm_dist_t_idx": signals["norm_dist_t_idx"],
                "norm_dist_t_mid": signals["norm_dist_t_mid"],
                "dist_ti": signals["dist_ti"],
                "d_idx_mid": signals["d_idx_mid"],
                "count_up": signals["count_up"],
                "target_action": target_action,
                "lm": lm_list,
                "summary": signals["summary"],
            }

        return annotated, gesture_name, debug_info

    @staticmethod
    def _dist(p1, p2) -> float:
        return math.hypot(p1.x - p2.x, p1.y - p2.y)

    @staticmethod
    def _vector_angle(v1: tuple[float, float], v2: tuple[float, float]) -> float:
        """Angle in degrees between two 2D vectors."""
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        m1 = math.hypot(v1[0], v1[1])
        m2 = math.hypot(v2[0], v2[1])
        if m1 * m2 == 0:
            return 0.0
        cos_angle = max(-1.0, min(1.0, dot / (m1 * m2)))
        return math.degrees(math.acos(cos_angle))

    def _check_two_hand_triangle(self, lmA: list, lmB: list) -> tuple[bool, dict]:
        """Check if index fingertips meet at apex and thumbs meet at base."""
        idxA, idxB = lmA[8], lmB[8]
        thbA, thbB = lmA[4], lmB[4]

        d_idx = self._dist(idxA, idxB)
        d_thumb = self._dist(thbA, thbB)
        hA = thbA.y - idxA.y
        hB = thbB.y - idxB.y

        is_triangle = bool(
            d_idx < 0.09
            and d_thumb < 0.09
            and hA > 0.035
            and hB > 0.035
            and self._dist(idxA, thbA) > 0.06
            and self._dist(idxB, thbB) > 0.06
        )
        return is_triangle, {"d_idx": d_idx, "d_thumb": d_thumb, "hA": hA, "hB": hB}

    def _get_palm_orientation(self, lm: list, handedness_label: str) -> tuple[str, float]:
        """
        Determine if the palm or back of hand faces the camera.
        In mirrored selfie view, MediaPipe handedness labels are inverted relative to physical hands.
        """
        t_tip = lm[4]
        p_mcp = lm[17]

        if handedness_label == "Left":
            x_diff = p_mcp.x - t_tip.x
        else:
            x_diff = t_tip.x - p_mcp.x

        if x_diff > 0.035:
            return "palm", x_diff
        elif x_diff < -0.035:
            return "back", x_diff
        else:
            return "edge", x_diff

    def _fingers_up(self, lm: list, handedness_label: str) -> tuple[list[bool], dict]:
        """Extract scale-invariant finger extension states with thumb hysteresis."""
        wrist = lm[0]
        t_tip, i_tip, m_tip, r_tip, p_tip = lm[4], lm[8], lm[12], lm[16], lm[20]
        t_ip, i_pip, m_pip, r_pip, p_pip = lm[3], lm[6], lm[10], lm[14], lm[18]
        t_mcp, i_mcp, m_mcp, r_mcp, p_mcp = lm[2], lm[5], lm[9], lm[13], lm[17]

        palm_scale = max(self._dist(wrist, m_mcp), 1e-5)

        dist_t_idx_raw = self._dist(t_tip, i_mcp)
        dist_t_mid_raw = self._dist(t_tip, m_mcp)
        dist_ti = self._dist(t_tip, i_tip)
        d_idx_mid = self._dist(i_tip, m_tip)

        norm_dist_t_idx = dist_t_idx_raw / palm_scale
        norm_dist_t_mid = dist_t_mid_raw / palm_scale

        v_thumb = (t_tip.x - t_mcp.x, t_tip.y - t_mcp.y)
        v_index = (i_tip.x - i_mcp.x, i_tip.y - i_mcp.y)
        thumb_index_angle = self._vector_angle(v_thumb, v_index)

        is_thumb_up_vert = (
            t_tip.y < t_ip.y - 0.02
            and t_tip.y < t_mcp.y - 0.025
            and t_tip.y < i_mcp.y - 0.025
            and t_tip.y < wrist.y
            and norm_dist_t_mid > 0.68
        )
        is_thumb_down_vert = (
            t_tip.y > t_ip.y + 0.02
            and t_tip.y > t_mcp.y + 0.025
            and t_tip.y > i_mcp.y + 0.025
            and t_tip.y > wrist.y
            and norm_dist_t_mid > 0.68
        )

        # Dead-zone hysteresis prevents rapid oscillation between curled and extended states
        is_thumb_extended_raw = (
            (norm_dist_t_idx > 0.46 or norm_dist_t_mid > 0.75)
            and dist_ti > 0.075
        ) or is_thumb_up_vert or is_thumb_down_vert

        is_thumb_curled_raw = (
            norm_dist_t_idx < 0.35
            and norm_dist_t_mid < 0.60
            and not is_thumb_up_vert
            and not is_thumb_down_vert
        )

        if is_thumb_extended_raw:
            self._last_thumb_state = True
        elif is_thumb_curled_raw:
            self._last_thumb_state = False

        thumb_bool = self._last_thumb_state

        idx_up = (i_tip.y < i_pip.y - 0.015) and (i_tip.y < i_mcp.y)
        idx_curled = (i_tip.y > i_pip.y - 0.005) or (self._dist(i_tip, wrist) < self._dist(i_pip, wrist) * 1.05)

        mid_up = (m_tip.y < m_pip.y - 0.015) and (m_tip.y < m_mcp.y)
        mid_curled = (m_tip.y > m_pip.y - 0.005) or (self._dist(m_tip, wrist) < self._dist(m_pip, wrist) * 1.05)

        ring_up = (r_tip.y < r_pip.y - 0.015) and (r_tip.y < r_mcp.y)
        ring_curled = (r_tip.y > r_pip.y - 0.015) or (self._dist(r_tip, wrist) < self._dist(r_pip, wrist) * 1.05)

        pky_up = (p_tip.y < p_pip.y - 0.015) and (p_tip.y < p_mcp.y)
        pky_curled = (p_tip.y > p_pip.y - 0.005) or (self._dist(p_tip, wrist) < self._dist(p_pip, wrist) * 1.05)

        fingers_bool = [thumb_bool, idx_up, mid_up, ring_up, pky_up]
        count_up = sum(1 for b in fingers_bool if b)

        orientation, x_diff = self._get_palm_orientation(lm, handedness_label)
        z_diff = m_mcp.z - wrist.z

        five_fingers_ext = bool(count_up == 5 and thumb_bool and idx_up and mid_up and ring_up and pky_up)

        signals = {
            "lm": lm,
            "wrist": wrist,
            "handedness": handedness_label,
            "fingers_bool": fingers_bool,
            "count_up": count_up,
            "five_fingers_ext": five_fingers_ext,
            "dist_ti": dist_ti,
            "d_idx_mid": d_idx_mid,
            "norm_dist_t_idx": norm_dist_t_idx,
            "norm_dist_t_mid": norm_dist_t_mid,
            "thumb_index_angle": thumb_index_angle,
            "is_thumb_up_vert": is_thumb_up_vert,
            "is_thumb_down_vert": is_thumb_down_vert,
            "idx_up": idx_up,
            "idx_curled": idx_curled,
            "mid_up": mid_up,
            "mid_curled": mid_curled,
            "ring_up": ring_up,
            "ring_curled": ring_curled,
            "pky_up": pky_up,
            "pky_curled": pky_curled,
            "x_diff": x_diff,
            "z_diff": z_diff,
            "orientation": orientation,
            "summary": f"T_idx:{norm_dist_t_idx:.2f} Angle:{thumb_index_angle:.0f}deg",
        }

        return fingers_bool, signals

    def _classify_gesture(self, sig: dict) -> str | None:
        """Map geometric signals to a single-hand gesture name."""
        t_up, i_up, m_up, r_up, p_up = sig["fingers_bool"]
        count_up = sig["count_up"]
        i_curled = sig["idx_curled"]
        m_curled = sig["mid_curled"]
        r_curled = sig["ring_curled"]
        p_curled = sig["pky_curled"]
        dist_ti = sig["dist_ti"]
        d_idx_mid = sig["d_idx_mid"]
        norm_t_idx = sig["norm_dist_t_idx"]
        angle = sig["thumb_index_angle"]
        orient = sig["orientation"]

        if count_up == 0 and not t_up and i_curled and m_curled and r_curled and p_curled:
            return "fist"

        if dist_ti < 0.065 and m_up and r_up and p_up and not m_curled and not r_curled and not p_curled:
            return "ok_sign"

        if sig["is_thumb_up_vert"] and i_curled and m_curled and r_curled and p_curled:
            return "thumbs_up"

        if sig["is_thumb_down_vert"] and i_curled and m_curled and r_curled and p_curled:
            return "thumbs_down"

        if count_up == 5 and t_up and i_up and m_up and r_up and p_up:
            if orient == "palm":
                return "open_palm"
            elif orient == "back":
                return "back_of_hand"
            return None

        # Peace sign ignores thumb position; proximity of index and middle tips separates peace from crossed fingers
        if i_up and m_up and r_curled and p_curled:
            if d_idx_mid < 0.052:
                return "crossed_fingers"
            return "two_fingers"

        if (
            t_up
            and i_up
            and m_curled
            and r_curled
            and p_curled
            and not p_up
            and 50.0 <= angle <= 135.0
            and dist_ti >= 0.095
            and norm_t_idx > 0.45
        ):
            return "l_sign"

        if i_up and p_up and m_curled and r_curled and not m_up:
            return "rock_sign"

        if i_up and m_up and r_up and p_curled and not p_up:
            return "three_fingers"

        if count_up == 4:
            return "four_fingers"

        if i_up and m_curled and r_curled and p_curled and not p_up:
            return "index_point"

        return None

    def close(self) -> None:
        self._hands.close()

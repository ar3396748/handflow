"""Hand geometry signature extraction, outlier rejection, and profile persistence."""

from __future__ import annotations

import json
import math
import os
import time


def _dist(p1, p2) -> float:
    return math.hypot(p1.x - p2.x, p1.y - p2.y)


def extract_hand_signature(lm: list) -> list[float] | None:
    """
    Extract a 13-dimensional scale-invariant ratio vector from 21 MediaPipe hand landmarks.
    Ratios cover normalized finger lengths, palm aspect ratio, knuckle spans, and spreads.
    """
    if len(lm) < 21:
        return None

    wrist = lm[0]
    t_tip, i_tip, m_tip, r_tip, p_tip = lm[4], lm[8], lm[12], lm[16], lm[20]
    t_mcp, i_mcp, m_mcp, r_mcp, p_mcp = lm[2], lm[5], lm[9], lm[13], lm[17]

    l_palm = _dist(wrist, m_mcp)
    w_palm = _dist(i_mcp, p_mcp)

    if l_palm < 1e-4 or w_palm < 1e-4:
        return None

    r_thumb = _dist(t_tip, t_mcp) / l_palm
    r_index = _dist(i_tip, i_mcp) / l_palm
    r_mid = _dist(m_tip, m_mcp) / l_palm
    r_ring = _dist(r_tip, r_mcp) / l_palm
    r_pinky = _dist(p_tip, p_mcp) / l_palm

    r_aspect = w_palm / l_palm

    r_k_5_9 = _dist(i_mcp, m_mcp) / w_palm
    r_k_9_13 = _dist(m_mcp, r_mcp) / w_palm
    r_k_13_17 = _dist(r_mcp, p_mcp) / w_palm

    r_s_4_8 = _dist(t_tip, i_tip) / l_palm
    r_s_8_12 = _dist(i_tip, m_tip) / l_palm
    r_s_12_16 = _dist(m_tip, r_tip) / l_palm
    r_s_16_20 = _dist(r_tip, p_tip) / l_palm

    return [
        round(r_thumb, 4),
        round(r_index, 4),
        round(r_mid, 4),
        round(r_ring, 4),
        round(r_pinky, 4),
        round(r_aspect, 4),
        round(r_k_5_9, 4),
        round(r_k_9_13, 4),
        round(r_k_13_17, 4),
        round(r_s_4_8, 4),
        round(r_s_8_12, 4),
        round(r_s_12_16, 4),
        round(r_s_16_20, 4),
    ]


def compute_similarity(sig_test: list[float], sig_ref: list[float]) -> float:
    """Compute normalized Euclidean similarity score in range [0.0, 1.0]."""
    if not sig_test or not sig_ref or len(sig_test) != len(sig_ref):
        return 0.0

    sq_err = sum((a - b) ** 2 for a, b in zip(sig_test, sig_ref))
    norm_ref = sum(b ** 2 for b in sig_ref)

    if norm_ref < 1e-6:
        return 0.0

    rel_error = math.sqrt(sq_err) / math.sqrt(norm_ref)
    similarity = max(0.0, min(1.0, 1.0 - rel_error * 1.6))
    return round(similarity, 4)


def filter_outliers_and_average(
    signatures: list[list[float]], z_threshold: float = 2.0
) -> tuple[list[float], int, int]:
    """Filter outlier frames across dimensions using Z-score and compute inlier mean."""
    n = len(signatures)
    if n == 0:
        return [], 0, 0
    if n < 4:
        dim = len(signatures[0])
        avg = [sum(sig[d] for sig in signatures) / n for d in range(dim)]
        return [round(x, 4) for x in avg], n, n

    dim = len(signatures[0])
    means = [sum(sig[d] for sig in signatures) / n for d in range(dim)]
    stds = [
        math.sqrt(sum((sig[d] - means[d]) ** 2 for sig in signatures) / n)
        for d in range(dim)
    ]

    inliers = []
    for sig in signatures:
        is_inlier = True
        for d in range(dim):
            sigma = max(stds[d], 1e-4)
            z = abs(sig[d] - means[d]) / sigma
            if z > z_threshold:
                is_inlier = False
                break
        if is_inlier:
            inliers.append(sig)

    # Prevent discarding too many samples in case of noisy captures
    if len(inliers) < max(3, int(n * 0.40)):
        inliers = signatures

    m = len(inliers)
    ref_vector = [sum(sig[d] for sig in inliers) / m for d in range(dim)]
    return [round(x, 4) for x in ref_vector], m, n


def save_profile(filepath: str, signature: list[float], metadata: dict | None = None) -> bool:
    """Save hand signature vector and metadata to JSON."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        payload = {
            "signature": signature,
            "dimension": len(signature),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "metadata": metadata or {},
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return True
    except Exception as exc:
        print(f"[HandSignature] Error saving profile: {exc}")
        return False


def load_profile(filepath: str) -> dict | None:
    """Load hand signature profile from JSON. Returns None on missing or invalid file."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            profile = json.load(f)
        if "signature" in profile and isinstance(profile["signature"], list) and len(profile["signature"]) == 13:
            return profile
        return None
    except Exception as exc:
        print(f"[HandSignature] Error loading profile: {exc}")
        return None

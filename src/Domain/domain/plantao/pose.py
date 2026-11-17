"""Ângulo de abdução do ombro e desvios do exercício."""
from __future__ import annotations

import math

_LEFT = {"shoulder": 11, "elbow": 13, "hip": 23}
_RIGHT = {"shoulder": 12, "elbow": 14, "hip": 24}


def joint_angle_deg(a, b, c) -> float:
    bax, bay = a[0] - b[0], a[1] - b[1]
    bcx, bcy = c[0] - b[0], c[1] - b[1]
    dot = bax * bcx + bay * bcy
    na = math.hypot(bax, bay) or 1e-9
    nc = math.hypot(bcx, bcy) or 1e-9
    cos = max(-1.0, min(1.0, dot / (na * nc)))
    return math.degrees(math.acos(cos))


def shoulder_abduction_deg(landmarks, side: str) -> float:
    idx = _LEFT if side == "left" else _RIGHT
    return joint_angle_deg(
        landmarks[idx["hip"]],
        landmarks[idx["shoulder"]],
        landmarks[idx["elbow"]],
    )


def posture_deviations(
    frames,
    *,
    target_deg: float = 90.0,
    tolerance_deg: float = 25.0,
    asymmetry_deg: float = 20.0,
) -> list[dict]:
    found = []
    for index, frame in enumerate(frames):
        left = shoulder_abduction_deg(frame, "left")
        right = shoulder_abduction_deg(frame, "right")
        if abs(left - right) > asymmetry_deg:
            found.append({
                "kind": "asymmetry",
                "frame": index,
                "detail": f"diferenca {abs(left - right):.0f} graus",
            })
        peak = max(left, right)
        if peak > target_deg + tolerance_deg:
            found.append({
                "kind": "overshoot",
                "frame": index,
                "detail": f"abducao {peak:.0f} graus, alvo {target_deg:.0f}",
            })
        elif peak < target_deg - tolerance_deg:
            found.append({
                "kind": "undershoot",
                "frame": index,
                "detail": f"abducao {peak:.0f} graus, alvo {target_deg:.0f}",
            })
    return found

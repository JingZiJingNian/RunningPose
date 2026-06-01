from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

import numpy as np

from .constants import POSE_LANDMARK_KEYS
from .utils import compute_derivative, distance2d, interpolate_series, midpoint, safe_mean, smooth_series


def get_landmark_xy(landmarks_2d: List[Dict[str, float]], landmark_idx: int) -> Optional[Dict[str, float]]:
    if not landmarks_2d:
        return None
    if landmark_idx < 0 or landmark_idx >= len(landmarks_2d):
        return None

    pt = landmarks_2d[landmark_idx]
    if not pt:
        return None

    x = pt.get("x")
    y = pt.get("y")
    visibility = pt.get("visibility", 1.0)

    if x is None or y is None:
        return None

    return {
        "x": float(x),
        "y": float(y),
        "visibility": float(visibility),
    }


def build_raw_time_series(frames_data: List[Dict[str, any]]) -> Dict[str, List[float]]:
    series = defaultdict(list)

    idx = POSE_LANDMARK_KEYS

    for frame in frames_data:
        lms = frame.get("landmarks_2d") or []
        t = frame.get("time", np.nan)

        ls = get_landmark_xy(lms, idx["left_shoulder"])
        rs = get_landmark_xy(lms, idx["right_shoulder"])
        lh = get_landmark_xy(lms, idx["left_hip"])
        rh = get_landmark_xy(lms, idx["right_hip"])
        lk = get_landmark_xy(lms, idx["left_knee"])
        rk = get_landmark_xy(lms, idx["right_knee"])
        la = get_landmark_xy(lms, idx["left_ankle"])
        ra = get_landmark_xy(lms, idx["right_ankle"])
        nose = get_landmark_xy(lms, idx["nose"])

        shoulder_mid = midpoint(ls, rs)
        pelvis_mid = midpoint(lh, rh)
        trunk_mid = midpoint(shoulder_mid, pelvis_mid)

        left_leg_len = distance2d(lh, la)
        right_leg_len = distance2d(rh, ra)
        trunk_len = distance2d(shoulder_mid, pelvis_mid)

        ref_len = safe_mean(
            [left_leg_len, right_leg_len, trunk_len],
            default=np.nan,
        )

        vis_vals = [
            p["visibility"]
            for p in [ls, rs, lh, rh, lk, rk, la, ra, nose]
            if p is not None
        ]
        frame_visibility = safe_mean(vis_vals, default=0.0)

        series["timestamps"].append(float(t))
        series["pelvis_x"].append(pelvis_mid["x"] if pelvis_mid else np.nan)
        series["pelvis_y"].append(pelvis_mid["y"] if pelvis_mid else np.nan)
        series["shoulder_x"].append(shoulder_mid["x"] if shoulder_mid else np.nan)
        series["shoulder_y"].append(shoulder_mid["y"] if shoulder_mid else np.nan)
        series["trunk_center_y"].append(trunk_mid["y"] if trunk_mid else np.nan)

        series["left_ankle_x"].append(la["x"] if la else np.nan)
        series["left_ankle_y"].append(la["y"] if la else np.nan)
        series["right_ankle_x"].append(ra["x"] if ra else np.nan)
        series["right_ankle_y"].append(ra["y"] if ra else np.nan)

        series["left_knee_x"].append(lk["x"] if lk else np.nan)
        series["left_knee_y"].append(lk["y"] if lk else np.nan)
        series["right_knee_x"].append(rk["x"] if rk else np.nan)
        series["right_knee_y"].append(rk["y"] if rk else np.nan)

        series["ref_length"].append(ref_len)
        series["frame_visibility"].append(frame_visibility)

    pelvis_x = np.array(series["pelvis_x"], dtype=float)
    pelvis_y = np.array(series["pelvis_y"], dtype=float)

    left_ankle_x = np.array(series["left_ankle_x"], dtype=float)
    left_ankle_y = np.array(series["left_ankle_y"], dtype=float)
    right_ankle_x = np.array(series["right_ankle_x"], dtype=float)
    right_ankle_y = np.array(series["right_ankle_y"], dtype=float)

    series["left_ankle_rel_x"] = (left_ankle_x - pelvis_x).tolist()
    series["right_ankle_rel_x"] = (right_ankle_x - pelvis_x).tolist()
    series["left_ankle_rel_y"] = (left_ankle_y - pelvis_y).tolist()
    series["right_ankle_rel_y"] = (right_ankle_y - pelvis_y).tolist()

    return dict(series)


def infer_fps_from_frames(frames_data: List[Dict[str, any]]) -> float:
    if len(frames_data) < 2:
        return 30.0
    t0 = frames_data[0].get("time", 0.0)
    t1 = frames_data[1].get("time", None)
    if t1 is None or t1 == t0:
        return 30.0
    return max(1.0, 1.0 / (t1 - t0))


def preprocess_time_series(raw_series: Dict[str, List[float]], fps: float) -> Dict[str, np.ndarray]:
    proc: Dict[str, np.ndarray] = {}

    for key, values in raw_series.items():
        arr = np.array(values, dtype=float)

        if key == "timestamps":
            proc[key] = arr
            continue

        arr = interpolate_series(arr)
        if key != "frame_visibility":
            arr = smooth_series(arr, window=7)

        proc[key] = arr

    ref_arr = proc.get("ref_length", np.array([], dtype=float))
    ref_length_mean = float(np.nanmedian(ref_arr)) if len(ref_arr) else 1.0
    if not np.isfinite(ref_length_mean) or ref_length_mean < 1e-6:
        ref_length_mean = 1.0
    proc["ref_length_mean"] = np.array([ref_length_mean], dtype=float)

    proc["left_ankle_rel_y_d1"] = compute_derivative(proc["left_ankle_rel_y"], fps)
    proc["right_ankle_rel_y_d1"] = compute_derivative(proc["right_ankle_rel_y"], fps)

    return proc
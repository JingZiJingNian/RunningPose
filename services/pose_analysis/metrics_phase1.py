from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from .constants import EPS, MODEL_VERSION
from .gait_events import pair_contact_and_flight
from .utils import clip01


def compute_cadence(events: Dict[str, Any], timestamps: np.ndarray) -> Dict[str, Any]:
    total_steps = len(events.get("left_ic", [])) + len(events.get("right_ic", []))

    if len(timestamps) < 2:
        return {"value": None, "unit": "spm", "confidence": 0.0, "total_steps": total_steps}

    duration = float(timestamps[-1] - timestamps[0])
    if duration <= 0:
        return {"value": None, "unit": "spm", "confidence": 0.0, "total_steps": total_steps}

    cadence = (total_steps / duration) * 60.0
    cadence = float(np.clip(cadence, 120.0, 220.0))

    return {
        "value": round(cadence, 1),
        "unit": "spm",
        "confidence": float(events.get("event_confidence", 0.0)),
        "total_steps": int(total_steps),
    }


def compute_ground_contact_time(events: Dict[str, Any], timestamps: np.ndarray) -> Dict[str, Any]:
    left_gct, _ = pair_contact_and_flight(events["left_ic"], events["left_to"], timestamps)
    right_gct, _ = pair_contact_and_flight(events["right_ic"], events["right_to"], timestamps)

    vals = left_gct + right_gct
    if not vals:
        return {"value": None, "unit": "ms", "confidence": 0.0}

    val_ms = 1000.0 * float(np.mean(vals))
    return {
        "value": round(val_ms, 1),
        "unit": "ms",
        "confidence": round(
            float(events.get("event_confidence", 0.0)) * clip01(len(vals) / 6.0),
            3,
        ),
    }


def compute_flight_time(events: Dict[str, Any], timestamps: np.ndarray) -> Dict[str, Any]:
    _, left_ft = pair_contact_and_flight(events["left_ic"], events["left_to"], timestamps)
    _, right_ft = pair_contact_and_flight(events["right_ic"], events["right_to"], timestamps)

    vals = left_ft + right_ft
    if not vals:
        return {"value": None, "unit": "ms", "confidence": 0.0}

    val_ms = 1000.0 * float(np.mean(vals))
    return {
        "value": round(val_ms, 1),
        "unit": "ms",
        "confidence": round(
            float(events.get("event_confidence", 0.0)) * clip01(len(vals) / 6.0),
            3,
        ),
    }


def compute_vertical_oscillation_rel(proc_series: Dict[str, np.ndarray]) -> Dict[str, Any]:
    y = np.asarray(proc_series["trunk_center_y"], dtype=float)
    ref = float(proc_series["ref_length_mean"][0])

    if len(y) < 10 or ref < EPS:
        return {"value": None, "unit": "body_scale", "confidence": 0.0}

    q95 = float(np.nanpercentile(y, 95))
    q05 = float(np.nanpercentile(y, 5))
    vo_rel = abs(q95 - q05) / ref

    visibility = float(np.nanmean(proc_series.get("frame_visibility", np.array([0.0], dtype=float))))
    return {
        "value": round(vo_rel, 4),
        "unit": "body_scale",
        "confidence": round(clip01(0.7 * visibility + 0.3), 3),
    }


def compute_trunk_lean_angle(proc_series: Dict[str, np.ndarray]) -> Dict[str, Any]:
    sx = np.asarray(proc_series["shoulder_x"], dtype=float)
    sy = np.asarray(proc_series["shoulder_y"], dtype=float)
    px = np.asarray(proc_series["pelvis_x"], dtype=float)
    py = np.asarray(proc_series["pelvis_y"], dtype=float)

    dx = sx - px
    dy = sy - py
    theta = np.degrees(np.arctan(np.abs(dx) / (np.abs(dy) + EPS)))

    if len(theta) == 0:
        return {"value": None, "unit": "deg", "confidence": 0.0}

    visibility = float(np.nanmean(proc_series.get("frame_visibility", np.array([0.0], dtype=float))))
    return {
        "value": round(float(np.nanmean(theta)), 2),
        "std": round(float(np.nanstd(theta)), 2),
        "unit": "deg",
        "confidence": round(clip01(visibility), 3),
    }


def compute_overstride_index(
    proc_series: Dict[str, np.ndarray],
    events: Dict[str, Any],
) -> Dict[str, Any]:
    pelvis_x = np.asarray(proc_series["pelvis_x"], dtype=float)
    left_ankle_x = np.asarray(proc_series["left_ankle_x"], dtype=float)
    right_ankle_x = np.asarray(proc_series["right_ankle_x"], dtype=float)
    leg_ref = float(proc_series["ref_length_mean"][0])

    if leg_ref < EPS:
        return {"value": None, "unit": "leg_scale", "confidence": 0.0}

    vals: List[float] = []

    for e in events.get("left_ic", []):
        idx = int(e["frame_idx"])
        if 0 <= idx < len(pelvis_x):
            vals.append((left_ankle_x[idx] - pelvis_x[idx]) / leg_ref)

    for e in events.get("right_ic", []):
        idx = int(e["frame_idx"])
        if 0 <= idx < len(pelvis_x):
            vals.append((right_ankle_x[idx] - pelvis_x[idx]) / leg_ref)

    if not vals:
        return {"value": None, "unit": "leg_scale", "confidence": 0.0}

    return {
        "value": round(float(np.nanmean(vals)), 4),
        "unit": "leg_scale",
        "confidence": round(
            float(events.get("event_confidence", 0.0)) * clip01(len(vals) / 6.0),
            3,
        ),
    }


def build_vertical_oscillation_wave(proc_series):
    timestamps = np.asarray(proc_series["timestamps"], dtype=float)
    y = np.asarray(proc_series["trunk_center_y"], dtype=float)
    ref = float(proc_series["ref_length_mean"][0])

    if len(timestamps) == 0 or ref < EPS:
        return {"x": [], "y": []}

    baseline = float(np.nanmedian(y))
    rel = (y - baseline) / ref

    return {
        "x": [round(float(t), 3) for t in timestamps],
        "y": [round(float(v), 5) if np.isfinite(v) else None for v in rel],
    }


def build_trunk_lean_wave(proc_series):
    timestamps = np.asarray(proc_series["timestamps"], dtype=float)
    sx = np.asarray(proc_series["shoulder_x"], dtype=float)
    sy = np.asarray(proc_series["shoulder_y"], dtype=float)
    px = np.asarray(proc_series["pelvis_x"], dtype=float)
    py = np.asarray(proc_series["pelvis_y"], dtype=float)

    dx = sx - px
    dy = sy - py
    theta = np.degrees(np.arctan(np.abs(dx) / (np.abs(dy) + EPS)))

    return {
        "x": [round(float(t), 3) for t in timestamps],
        "y": [round(float(v), 4) if np.isfinite(v) else None for v in theta],
    }


def build_step_metric_series(events, timestamps, proc_series):
    left_ic = events.get("left_ic", [])
    right_ic = events.get("right_ic", [])
    left_to = events.get("left_to", [])
    right_to = events.get("right_to", [])

    pelvis_x = np.asarray(proc_series["pelvis_x"], dtype=float)
    left_ankle_x = np.asarray(proc_series["left_ankle_x"], dtype=float)
    right_ankle_x = np.asarray(proc_series["right_ankle_x"], dtype=float)
    leg_ref = float(proc_series["ref_length_mean"][0])

    def event_times(event_list):
        out = []
        for e in event_list:
            idx = int(e["frame_idx"])
            if 0 <= idx < len(timestamps):
                out.append((idx, float(timestamps[idx])))
        return out

    left_ic_t = event_times(left_ic)
    right_ic_t = event_times(right_ic)
    left_to_t = event_times(left_to)
    right_to_t = event_times(right_to)

    cadence_scatter = []
    stride_scatter = []
    gct_scatter = []
    ft_scatter = []

    all_ic = sorted(
        [(idx, t, "L") for idx, t in left_ic_t] +
        [(idx, t, "R") for idx, t in right_ic_t],
        key=lambda x: x[1]
    )

    for i in range(1, len(all_ic)):
        prev_t = all_ic[i - 1][1]
        cur_t = all_ic[i][1]
        dt = cur_t - prev_t
        if dt > 0:
            inst_cadence = 60.0 / dt
            cadence_scatter.append({
                "x": round(cur_t, 3),
                "y": round(inst_cadence, 3),
            })

    for idx, t, side in all_ic:
        if leg_ref < EPS:
            continue

        if side == "L":
            val = (left_ankle_x[idx] - pelvis_x[idx]) / leg_ref if 0 <= idx < len(pelvis_x) else np.nan
        else:
            val = (right_ankle_x[idx] - pelvis_x[idx]) / leg_ref if 0 <= idx < len(pelvis_x) else np.nan

        if np.isfinite(val):
            stride_scatter.append({
                "x": round(t, 3),
                "y": round(float(val), 5),
            })

    def pair_contact_and_flight_local(ic_list, to_list):
        gct_vals, ft_vals = [], []
        ti = 0
        for i in range(len(ic_list) - 1):
            _, ic_t = ic_list[i]
            _, next_ic_t = ic_list[i + 1]

            while ti < len(to_list) and to_list[ti][1] <= ic_t:
                ti += 1
            if ti >= len(to_list):
                break

            _, to_t = to_list[ti]
            if ic_t < to_t < next_ic_t:
                gct_vals.append((to_t, (to_t - ic_t) * 1000.0))
                ft_vals.append((next_ic_t, (next_ic_t - to_t) * 1000.0))
        return gct_vals, ft_vals

    lgct, lft = pair_contact_and_flight_local(left_ic_t, left_to_t)
    rgct, rft = pair_contact_and_flight_local(right_ic_t, right_to_t)

    for t, val in lgct + rgct:
        gct_scatter.append({"x": round(t, 3), "y": round(val, 3)})

    for t, val in lft + rft:
        ft_scatter.append({"x": round(t, 3), "y": round(val, 3)})

    return {
        "cadence_scatter": cadence_scatter,
        "stride_length_scatter": stride_scatter,
        "ground_contact_time_scatter": gct_scatter,
        "flight_time_scatter": ft_scatter,
    }


def compute_phase1_metrics(proc_series, gait_events, fps):
    timestamps = np.asarray(proc_series["timestamps"], dtype=float)

    cadence = compute_cadence(gait_events, timestamps)
    gct = compute_ground_contact_time(gait_events, timestamps)
    ft = compute_flight_time(gait_events, timestamps)
    vo = compute_vertical_oscillation_rel(proc_series)
    trunk = compute_trunk_lean_angle(proc_series)
    osi = compute_overstride_index(proc_series, gait_events)

    vertical_wave = build_vertical_oscillation_wave(proc_series)
    trunk_wave = build_trunk_lean_wave(proc_series)
    step_series = build_step_metric_series(gait_events, timestamps, proc_series)

    event_conf = float(gait_events.get("event_confidence", 0.0))
    if event_conf >= 0.65:
        quality = "good"
    elif event_conf >= 0.35:
        quality = "fair"
    else:
        quality = "low"

    return {
        "phase": 1,
        "model_version": MODEL_VERSION,
        "analysis_quality": quality,

        "cadence": cadence,
        "ground_contact_time": gct,
        "flight_time": ft,
        "vertical_oscillation_rel": vo,
        "trunk_lean_angle": trunk,
        "overstride_index": osi,

        "event_summary": {
            "left_ic_count": len(gait_events.get("left_ic", [])),
            "right_ic_count": len(gait_events.get("right_ic", [])),
            "left_to_count": len(gait_events.get("left_to", [])),
            "right_to_count": len(gait_events.get("right_to", [])),
            "event_confidence": event_conf,
        },

        "timeseries": {
            "vertical_oscillation_wave": vertical_wave,
            "trunk_lean_angle_wave": trunk_wave,
            **step_series,
        },

        "total_analyzed_frames": int(len(timestamps)),
    }


def empty_metrics_payload() -> Dict[str, Any]:
    return {
        "phase": 1,
        "model_version": MODEL_VERSION,
        "analysis_quality": "low",
        "cadence": {"value": None, "unit": "spm", "confidence": 0.0, "total_steps": 0},
        "ground_contact_time": {"value": None, "unit": "ms", "confidence": 0.0},
        "flight_time": {"value": None, "unit": "ms", "confidence": 0.0},
        "vertical_oscillation_rel": {"value": None, "unit": "body_scale", "confidence": 0.0},
        "trunk_lean_angle": {"value": None, "std": None, "unit": "deg", "confidence": 0.0},
        "overstride_index": {"value": None, "unit": "leg_scale", "confidence": 0.0},
        "event_summary": {
            "left_ic_count": 0,
            "right_ic_count": 0,
            "left_to_count": 0,
            "right_to_count": 0,
            "event_confidence": 0.0,
        },
        "timeseries": {
            "vertical_oscillation_wave": {"x": [], "y": []},
            "trunk_lean_angle_wave": {"x": [], "y": []},
            "cadence_scatter": [],
            "stride_length_scatter": [],
            "ground_contact_time_scatter": [],
            "flight_time_scatter": [],
        },
        "step_records": [],
        "total_analyzed_frames": 0,
    }
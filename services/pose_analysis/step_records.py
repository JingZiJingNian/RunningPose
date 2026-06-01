from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np

from .constants import EPS


def events_to_times(event_list: List[Dict[str, float]], timestamps: np.ndarray) -> List[Tuple[int, float, float]]:
    out = []
    for e in event_list:
        idx = int(e["frame_idx"])
        if 0 <= idx < len(timestamps):
            out.append(
                (
                    idx,
                    float(timestamps[idx]),
                    float(e.get("confidence", 0.0)),
                )
            )
    return out


def _pair_step_events(
    ic_events: List[Tuple[int, float, float]],
    to_events: List[Tuple[int, float, float]],
) -> List[Tuple[Tuple[int, float, float], Tuple[int, float, float], Tuple[int, float, float]]]:
    pairs = []
    ti = 0

    for i in range(len(ic_events) - 1):
        ic0 = ic_events[i]
        ic1 = ic_events[i + 1]
        ic0_time = ic0[1]
        ic1_time = ic1[1]

        while ti < len(to_events) and to_events[ti][1] <= ic0_time:
            ti += 1
        if ti >= len(to_events):
            break

        to_ev = to_events[ti]
        to_time = to_ev[1]

        if ic0_time < to_time < ic1_time:
            pairs.append((ic0, to_ev, ic1))

    return pairs


def _safe_slice(arr: np.ndarray, start_idx: int, end_idx: int) -> np.ndarray:
    start_idx = max(0, start_idx)
    end_idx = min(len(arr), end_idx)
    if end_idx <= start_idx:
        return np.array([], dtype=float)
    return arr[start_idx:end_idx]


def _nanmean_or_none(arr: np.ndarray):
    if arr.size == 0:
        return None
    val = float(np.nanmean(arr))
    return val if np.isfinite(val) else None


def build_step_records(
    proc_series: Dict[str, np.ndarray],
    gait_events: Dict[str, Any],
    timestamps: np.ndarray,
) -> List[Dict[str, Any]]:
    """
    第一版步级记录层：
    每条记录对应“某一只脚从 IC 到下一次同侧 IC”的一步。
    """
    timestamps = np.asarray(timestamps, dtype=float)

    left_ic = events_to_times(gait_events.get("left_ic", []), timestamps)
    right_ic = events_to_times(gait_events.get("right_ic", []), timestamps)
    left_to = events_to_times(gait_events.get("left_to", []), timestamps)
    right_to = events_to_times(gait_events.get("right_to", []), timestamps)

    left_steps = _pair_step_events(left_ic, left_to)
    right_steps = _pair_step_events(right_ic, right_to)

    pelvis_x = np.asarray(proc_series["pelvis_x"], dtype=float)
    trunk_lean_wave = np.degrees(
        np.arctan(
            np.abs(np.asarray(proc_series["shoulder_x"], dtype=float) - np.asarray(proc_series["pelvis_x"], dtype=float)) /
            (np.abs(np.asarray(proc_series["shoulder_y"], dtype=float) - np.asarray(proc_series["pelvis_y"], dtype=float)) + EPS)
        )
    )

    trunk_center_y = np.asarray(proc_series["trunk_center_y"], dtype=float)
    ref_len = float(proc_series["ref_length_mean"][0])

    left_ankle_x = np.asarray(proc_series["left_ankle_x"], dtype=float)
    right_ankle_x = np.asarray(proc_series["right_ankle_x"], dtype=float)

    records: List[Dict[str, Any]] = []

    def build_one(side: str, triple, step_index: int):
        ic0, to_ev, ic1 = triple
        ic_frame, ic_time, ic_conf = ic0
        to_frame, to_time, to_conf = to_ev
        next_ic_frame, next_ic_time, _ = ic1

        stance_ms = (to_time - ic_time) * 1000.0
        flight_ms = (next_ic_time - to_time) * 1000.0
        step_ms = (next_ic_time - ic_time) * 1000.0
        instant_cadence = 60.0 / max((next_ic_time - ic_time), EPS)

        if side == "L":
            ankle_x_at_ic = float(left_ankle_x[ic_frame]) if 0 <= ic_frame < len(left_ankle_x) else np.nan
        else:
            ankle_x_at_ic = float(right_ankle_x[ic_frame]) if 0 <= ic_frame < len(right_ankle_x) else np.nan

        pelvis_x_at_ic = float(pelvis_x[ic_frame]) if 0 <= ic_frame < len(pelvis_x) else np.nan

        if np.isfinite(ankle_x_at_ic) and np.isfinite(pelvis_x_at_ic) and ref_len > EPS:
            overstride_index = (ankle_x_at_ic - pelvis_x_at_ic) / ref_len
        else:
            overstride_index = None

        trunk_slice = _safe_slice(trunk_lean_wave, ic_frame, next_ic_frame + 1)
        trunk_lean_mean = _nanmean_or_none(trunk_slice)
        trunk_lean_std = float(np.nanstd(trunk_slice)) if trunk_slice.size else None
        trunk_lean_at_ic = float(trunk_lean_wave[ic_frame]) if 0 <= ic_frame < len(trunk_lean_wave) else None

        vo_local = None
        y_slice = _safe_slice(trunk_center_y, ic_frame, next_ic_frame + 1)
        if y_slice.size and ref_len > EPS:
            q95 = float(np.nanpercentile(y_slice, 95))
            q05 = float(np.nanpercentile(y_slice, 5))
            vo_local = abs(q95 - q05) / ref_len

        return {
            "step_index": int(step_index),
            "side": side,

            "ic_frame": int(ic_frame),
            "ic_time": round(float(ic_time), 3),
            "to_frame": int(to_frame),
            "to_time": round(float(to_time), 3),
            "next_ic_frame": int(next_ic_frame),
            "next_ic_time": round(float(next_ic_time), 3),

            "stance_duration_ms": round(float(stance_ms), 3),
            "flight_duration_ms": round(float(flight_ms), 3),
            "step_duration_ms": round(float(step_ms), 3),
            "instant_cadence_spm": round(float(instant_cadence), 3),

            "overstride_index": round(float(overstride_index), 5) if overstride_index is not None and np.isfinite(overstride_index) else None,
            "trunk_lean_at_ic_deg": round(float(trunk_lean_at_ic), 4) if trunk_lean_at_ic is not None and np.isfinite(trunk_lean_at_ic) else None,
            "trunk_lean_mean_deg": round(float(trunk_lean_mean), 4) if trunk_lean_mean is not None else None,
            "trunk_lean_std_deg": round(float(trunk_lean_std), 4) if trunk_lean_std is not None and np.isfinite(trunk_lean_std) else None,
            "vertical_oscillation_local": round(float(vo_local), 5) if vo_local is not None and np.isfinite(vo_local) else None,

            "pelvis_x_at_ic": round(float(pelvis_x_at_ic), 5) if np.isfinite(pelvis_x_at_ic) else None,
            "ankle_x_at_ic": round(float(ankle_x_at_ic), 5) if np.isfinite(ankle_x_at_ic) else None,

            "ic_confidence": round(float(ic_conf), 4),
            "to_confidence": round(float(to_conf), 4),
        }

    idx = 0
    for triple in left_steps:
        records.append(build_one("L", triple, idx))
        idx += 1

    for triple in right_steps:
        records.append(build_one("R", triple, idx))
        idx += 1

    records.sort(key=lambda r: r["ic_time"])
    for i, r in enumerate(records):
        r["step_index"] = i

    return records
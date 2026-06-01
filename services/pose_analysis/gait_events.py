from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np

from .utils import clip01


def find_local_minima(arr: np.ndarray, min_distance: int = 8) -> List[int]:
    arr = np.asarray(arr, dtype=float)
    candidates = []

    for i in range(1, len(arr) - 1):
        if np.isnan(arr[i - 1]) or np.isnan(arr[i]) or np.isnan(arr[i + 1]):
            continue
        if arr[i] <= arr[i - 1] and arr[i] <= arr[i + 1]:
            candidates.append(i)

    filtered: List[int] = []
    for idx in candidates:
        if not filtered:
            filtered.append(idx)
            continue

        if idx - filtered[-1] >= min_distance:
            filtered.append(idx)
        else:
            if arr[idx] < arr[filtered[-1]]:
                filtered[-1] = idx

    return filtered


def detect_foot_events(
    rel_y: np.ndarray,
    rel_x: np.ndarray,
    rel_y_d1: np.ndarray,
    fps: float,
    side: str = "left",
) -> Dict[str, List[Dict[str, float]]]:
    rel_y = np.asarray(rel_y, dtype=float)
    rel_x = np.asarray(rel_x, dtype=float)
    rel_y_d1 = np.asarray(rel_y_d1, dtype=float)

    same_foot_cycle_frames = max(int(0.55 * fps), 6)
    minima = find_local_minima(rel_y, min_distance=same_foot_cycle_frames)

    ic_events: List[Dict[str, float]] = []
    rel_x_median = float(np.nanmedian(rel_x)) if len(rel_x) else 0.0

    for idx in minima:
        left = max(0, idx - 2)
        right = min(len(rel_y), idx + 3)

        local_mean = float(np.nanmean(rel_y[left:right])) if right > left else float(rel_y[idx])
        prominence = local_mean - float(rel_y[idx])
        local_forward = float(rel_x[idx] - rel_x_median)

        score_shape = clip01(prominence / 0.01)
        score_forward = clip01((local_forward + 0.02) / 0.06)
        score = 0.6 * score_shape + 0.4 * score_forward

        if score >= 0.25:
            ic_events.append(
                {
                    "frame_idx": int(idx),
                    "confidence": float(score),
                }
            )

    to_events: List[Dict[str, float]] = []
    for i in range(len(ic_events) - 1):
        ic0 = ic_events[i]["frame_idx"]
        ic1 = ic_events[i + 1]["frame_idx"]

        if ic1 <= ic0 + 2:
            continue

        search_start = ic0 + max(1, int(0.10 * fps))
        search_end = min(ic1 - 1, ic0 + int(0.55 * (ic1 - ic0)))

        if search_end <= search_start:
            continue

        segment = rel_y_d1[search_start:search_end]
        if len(segment) == 0 or np.all(np.isnan(segment)):
            continue

        local_idx = int(np.nanargmax(segment))
        to_idx = search_start + local_idx
        rise_strength = float(segment[local_idx])

        score = clip01(rise_strength / 0.08)
        to_events.append(
            {
                "frame_idx": int(to_idx),
                "confidence": float(score),
            }
        )

    return {"ic": ic_events, "to": to_events}


def postprocess_event_sequence(
    left_events: Dict[str, List[Dict[str, float]]],
    right_events: Dict[str, List[Dict[str, float]]],
    fps: float,
) -> Dict[str, Any]:
    return {
        "left_ic": left_events["ic"],
        "left_to": left_events["to"],
        "right_ic": right_events["ic"],
        "right_to": right_events["to"],
    }


def detect_gait_events(proc_series: Dict[str, np.ndarray], fps: float) -> Dict[str, Any]:
    left_events = detect_foot_events(
        rel_y=proc_series["left_ankle_rel_y"],
        rel_x=proc_series["left_ankle_rel_x"],
        rel_y_d1=proc_series["left_ankle_rel_y_d1"],
        fps=fps,
        side="left",
    )
    right_events = detect_foot_events(
        rel_y=proc_series["right_ankle_rel_y"],
        rel_x=proc_series["right_ankle_rel_x"],
        rel_y_d1=proc_series["right_ankle_rel_y_d1"],
        fps=fps,
        side="right",
    )

    events = postprocess_event_sequence(left_events, right_events, fps)

    visibility = float(np.nanmean(proc_series.get("frame_visibility", np.array([0.0], dtype=float))))
    left_ic_n = len(events["left_ic"])
    right_ic_n = len(events["right_ic"])

    if left_ic_n + right_ic_n == 0:
        event_confidence = 0.0
    else:
        balance = 1.0 - abs(left_ic_n - right_ic_n) / max(left_ic_n + right_ic_n, 1)
        event_confidence = clip01(0.55 * visibility + 0.45 * balance)

    events["event_confidence"] = event_confidence
    return events


def events_to_times(event_list: List[Dict[str, float]], timestamps: np.ndarray) -> List[float]:
    times = []
    for e in event_list:
        idx = int(e["frame_idx"])
        if 0 <= idx < len(timestamps):
            times.append(float(timestamps[idx]))
    return times


def pair_contact_and_flight(
    ic_events: List[Dict[str, float]],
    to_events: List[Dict[str, float]],
    timestamps: np.ndarray,
) -> Tuple[List[float], List[float]]:
    ic_times = events_to_times(ic_events, timestamps)
    to_times = events_to_times(to_events, timestamps)

    gct_vals: List[float] = []
    ft_vals: List[float] = []

    ti = 0
    for i in range(len(ic_times) - 1):
        ic_t = ic_times[i]
        next_ic_t = ic_times[i + 1]

        while ti < len(to_times) and to_times[ti] <= ic_t:
            ti += 1
        if ti >= len(to_times):
            break

        to_t = to_times[ti]
        if ic_t < to_t < next_ic_t:
            gct_vals.append(to_t - ic_t)
            ft_vals.append(next_ic_t - to_t)

    return gct_vals, ft_vals
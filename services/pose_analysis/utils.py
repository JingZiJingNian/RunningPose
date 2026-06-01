from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np


def clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def safe_mean(values: List[Optional[float]], default: float = 0.0) -> float:
    vals = [float(v) for v in values if v is not None and not np.isnan(v)]
    return float(np.mean(vals)) if vals else float(default)


def midpoint(p1: Optional[Dict[str, float]], p2: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
    if not p1 or not p2:
        return None
    return {
        "x": (p1["x"] + p2["x"]) / 2.0,
        "y": (p1["y"] + p2["y"]) / 2.0,
        "visibility": min(p1.get("visibility", 1.0), p2.get("visibility", 1.0)),
    }


def distance2d(p1: Optional[Dict[str, float]], p2: Optional[Dict[str, float]]) -> Optional[float]:
    if not p1 or not p2:
        return None
    return math.sqrt((p1["x"] - p2["x"]) ** 2 + (p1["y"] - p2["y"]) ** 2)


def interpolate_series(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=float)
    valid = ~np.isnan(arr)
    if valid.sum() < 2:
        return arr.copy()

    idx = np.arange(len(arr))
    return np.interp(idx, idx[valid], arr[valid])


def smooth_series(arr: np.ndarray, window: int = 7) -> np.ndarray:
    arr = np.asarray(arr, dtype=float)
    if len(arr) < window or window < 3:
        return arr.copy()

    pad = window // 2
    padded = np.pad(arr, (pad, pad), mode="edge")
    kernel = np.ones(window, dtype=float) / window
    return np.convolve(padded, kernel, mode="valid")


def compute_derivative(arr: np.ndarray, fps: float) -> np.ndarray:
    arr = np.asarray(arr, dtype=float)
    if len(arr) < 2:
        return np.zeros_like(arr)
    dt = 1.0 / max(fps, 1.0)
    return np.gradient(arr, dt)


def resolve_video_path(video_file) -> str:
    if hasattr(video_file, "path"):
        return str(video_file.path)
    return str(video_file)
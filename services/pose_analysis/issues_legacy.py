from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

import numpy as np


def metric_value(metrics: Dict[str, Any], key: str) -> Optional[float]:
    item = metrics.get(key)
    if isinstance(item, dict):
        value = item.get("value")
        if value is None:
            return None
        return float(value)
    return None


def summarize_issues(
    per_frame_issues: List[Dict[str, Any]],
    metrics: Dict[str, Any],
) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for issue in per_frame_issues:
        grouped[issue["type"]].append(issue)

    summary: List[Dict[str, Any]] = []

    for issue_type, items in grouped.items():
        if not items:
            continue

        timestamps = [float(i.get("timestamp", 0.0)) for i in items]
        confs = [float(i.get("confidence", 0.0)) for i in items]
        severities = [i.get("severity", "low") for i in items]

        severity_rank = {"low": 1, "medium": 2, "high": 3}
        max_severity = max(severities, key=lambda s: severity_rank.get(s, 1))

        summary.append(
            {
                "type": issue_type,
                "severity": max_severity,
                "message": items[0]["message"],
                "suggestion": items[0]["suggestion"],
                "confidence": round(float(np.mean(confs)), 3),
                "occurrences": int(len(items)),
                "first_timestamp": round(min(timestamps), 2),
                "last_timestamp": round(max(timestamps), 2),
            }
        )

    cadence = metric_value(metrics, "cadence")
    gct = metric_value(metrics, "ground_contact_time")
    flight = metric_value(metrics, "flight_time")
    trunk = metric_value(metrics, "trunk_lean_angle")
    osi = metric_value(metrics, "overstride_index")
    vo = metric_value(metrics, "vertical_oscillation_rel")

    if cadence is not None and cadence < 155:
        summary.append(
            {
                "type": "low_cadence",
                "severity": "medium",
                "message": f"步频偏低（{cadence:.1f} spm）",
                "suggestion": "可尝试逐步提高步频，减少单步滞空和过度前伸。",
                "confidence": 0.78,
            }
        )

    if trunk is not None and trunk > 16:
        summary.append(
            {
                "type": "excessive_forward_lean",
                "severity": "medium",
                "message": f"躯干前倾偏大（{trunk:.1f}°）",
                "suggestion": "检查髋部驱动与核心支撑，避免折腰式前倾。",
                "confidence": 0.82,
            }
        )

    if osi is not None and osi > 0.32:
        summary.append(
            {
                "type": "overstride",
                "severity": "medium",
                "message": f"存在过度跨步倾向（指数 {osi:.3f}）",
                "suggestion": "尝试提高步频、缩短前伸距离，让落脚点更接近身体下方。",
                "confidence": 0.85,
            }
        )

    if gct is not None and gct > 290:
        summary.append(
            {
                "type": "long_ground_contact",
                "severity": "low",
                "message": f"触地时间偏长（{gct:.1f} ms）",
                "suggestion": "加强弹性反应和下肢刚度训练，改善触地后的回弹效率。",
                "confidence": 0.76,
            }
        )

    if flight is not None and flight < 60:
        summary.append(
            {
                "type": "limited_flight_phase",
                "severity": "low",
                "message": f"腾空时间较短（{flight:.1f} ms）",
                "suggestion": "结合步频、触地时间和落脚位置一起评估，不必单独追求更长腾空。",
                "confidence": 0.65,
            }
        )

    if vo is not None and vo > 0.16:
        summary.append(
            {
                "type": "excessive_vertical_oscillation",
                "severity": "low",
                "message": f"垂直振幅相对偏大（{vo:.3f}）",
                "suggestion": "关注向前推进效率，减少上下弹跳造成的能量浪费。",
                "confidence": 0.72,
            }
        )

    severity_rank = {"high": 3, "medium": 2, "low": 1}
    summary.sort(
        key=lambda x: (
            severity_rank.get(x.get("severity", "low"), 1),
            float(x.get("confidence", 0.0)),
        ),
        reverse=True,
    )

    return summary[:10]
from __future__ import annotations

from typing import Any, Dict, List

from .metrics_phase1 import empty_metrics_payload


def generate_fallback_data(video_info: Dict[str, Any]) -> Dict[str, Any]:
    frames: List[Dict[str, Any]] = []
    for i in range(10):
        frames.append(
            {
                "frame": i * 10,
                "time": round(i * 0.5, 2),
                "landmarks_2d": [],
                "landmarks_3d": [],
                "body_metrics": {
                    "shoulder_width": 0.4,
                    "hip_width": 0.3,
                },
            }
        )

    return {
        "video_info": video_info,
        "frames": frames,
        "metrics": empty_metrics_payload(),
        "issues": [
            {
                "type": "demo_data",
                "severity": "low",
                "message": "这是回退/演示数据，实际分析未成功完成。",
                "suggestion": "请确保视频清晰、主体完整可见、拍摄角度尽量稳定并接近侧视。",
                "confidence": 0.8,
                "timestamp": 0.0,
            }
        ],
    }
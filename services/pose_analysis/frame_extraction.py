from __future__ import annotations

from typing import Any, Dict, List

import numpy as np


def serialize_landmarks_2d(pose_landmarks) -> List[Dict[str, float]]:
    data = []
    for lm in pose_landmarks.landmark:
        data.append(
            {
                "x": float(lm.x),
                "y": float(lm.y),
                "z": float(lm.z),
                "visibility": float(getattr(lm, "visibility", 1.0)),
            }
        )
    return data


def serialize_landmarks_3d(pose_world_landmarks) -> List[Dict[str, float]]:
    data = []
    for lm in pose_world_landmarks.landmark:
        data.append(
            {
                "x": float(lm.x),
                "y": float(lm.y),
                "z": float(lm.z),
                "visibility": float(getattr(lm, "visibility", 1.0)),
            }
        )
    return data


def calculate_body_metrics(mp_pose, world_landmarks) -> Dict[str, float]:
    metrics = {}

    try:
        LEFT_SHOULDER = mp_pose.PoseLandmark.LEFT_SHOULDER.value
        RIGHT_SHOULDER = mp_pose.PoseLandmark.RIGHT_SHOULDER.value
        LEFT_HIP = mp_pose.PoseLandmark.LEFT_HIP.value
        RIGHT_HIP = mp_pose.PoseLandmark.RIGHT_HIP.value

        ls = world_landmarks.landmark[LEFT_SHOULDER]
        rs = world_landmarks.landmark[RIGHT_SHOULDER]
        lh = world_landmarks.landmark[LEFT_HIP]
        rh = world_landmarks.landmark[RIGHT_HIP]

        metrics["shoulder_width"] = float(
            np.sqrt((ls.x - rs.x) ** 2 + (ls.y - rs.y) ** 2 + (ls.z - rs.z) ** 2)
        )
        metrics["hip_width"] = float(
            np.sqrt((lh.x - rh.x) ** 2 + (lh.y - rh.y) ** 2 + (lh.z - rh.z) ** 2)
        )
    except Exception:
        pass

    return metrics


def extract_frame_data(mp_pose, results, frame_idx: int, frame_time: float) -> Dict[str, Any]:
    frame_data = {
        "frame": int(frame_idx),
        "time": float(frame_time),
        "landmarks_2d": [],
        "landmarks_3d": [],
        "body_metrics": {},
    }

    if results.pose_landmarks:
        frame_data["landmarks_2d"] = serialize_landmarks_2d(results.pose_landmarks)

    if results.pose_world_landmarks:
        frame_data["landmarks_3d"] = serialize_landmarks_3d(results.pose_world_landmarks)
        frame_data["body_metrics"] = calculate_body_metrics(mp_pose, results.pose_world_landmarks)

    return frame_data


def analyze_running_pose_legacy(mp_pose, results, current_time: float) -> List[Dict[str, Any]]:
    """
    旧版逐帧问题检测，先保留作为兼容层。
    第二阶段会逐步替换成基于步级记录和多指标证据融合的新诊断。
    """
    issues: List[Dict[str, Any]] = []

    if not results or not results.pose_landmarks:
        return issues

    try:
        lms = results.pose_landmarks.landmark
        PL = mp_pose.PoseLandmark

        left_shoulder = lms[PL.LEFT_SHOULDER.value]
        right_shoulder = lms[PL.RIGHT_SHOULDER.value]
        left_hip = lms[PL.LEFT_HIP.value]
        right_hip = lms[PL.RIGHT_HIP.value]
        left_elbow = lms[PL.LEFT_ELBOW.value]
        right_elbow = lms[PL.RIGHT_ELBOW.value]
        left_ankle = lms[PL.LEFT_ANKLE.value]
        right_ankle = lms[PL.RIGHT_ANKLE.value]

        shoulder_height_diff = abs(left_shoulder.y - right_shoulder.y)
        if shoulder_height_diff > 0.05:
            issues.append(
                {
                    "type": "shoulder_imbalance",
                    "severity": "medium",
                    "message": f"肩部高度不平衡（差值 {shoulder_height_diff:.3f}）",
                    "suggestion": "注意双肩放松，检查核心控制和摆臂对称性。",
                    "confidence": round(min(shoulder_height_diff * 10, 1.0), 3),
                    "timestamp": float(current_time),
                }
            )

        hip_height_diff = abs(left_hip.y - right_hip.y)
        if hip_height_diff > 0.03:
            issues.append(
                {
                    "type": "hip_imbalance",
                    "severity": "medium",
                    "message": f"骨盆左右高度差较明显（差值 {hip_height_diff:.3f}）",
                    "suggestion": "加强臀中肌与核心稳定训练，提升单腿支撑稳定性。",
                    "confidence": round(min(hip_height_diff * 15, 1.0), 3),
                    "timestamp": float(current_time),
                }
            )

        if left_elbow.x < 0.15 or right_elbow.x > 0.85:
            issues.append(
                {
                    "type": "excessive_arm_swing",
                    "severity": "low",
                    "message": "手臂横向摆动偏大",
                    "suggestion": "摆臂应以前后方向为主，避免横向拉扯身体。",
                    "confidence": 0.7,
                    "timestamp": float(current_time),
                }
            )

        ankle_width = abs(left_ankle.x - right_ankle.x)
        hip_width = abs(left_hip.x - right_hip.x)
        if hip_width > 1e-6 and ankle_width / hip_width > 2.4:
            issues.append(
                {
                    "type": "wide_step_width",
                    "severity": "low",
                    "message": "双脚落点横向间距偏大",
                    "suggestion": "尝试维持更稳定的骨盆控制和更紧凑的落脚轨迹。",
                    "confidence": 0.65,
                    "timestamp": float(current_time),
                }
            )

    except Exception:
        pass

    return issues
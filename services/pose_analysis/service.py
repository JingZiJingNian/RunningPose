from __future__ import annotations

import traceback
from typing import Any, Dict, Optional

import cv2
import mediapipe as mp
import numpy as np

from .diagnostics_phase2 import diagnose_phase2_issues
from .fallback import generate_fallback_data
from .frame_extraction import extract_frame_data
from .gait_events import detect_gait_events
from .metrics_phase1 import compute_phase1_metrics
from .step_records import build_step_records
from .timeseries import build_raw_time_series, infer_fps_from_frames, preprocess_time_series
from .utils import resolve_video_path


class PoseAnalysisService:
    """
    跑步姿态分析服务（Phase 2 主诊断版）
    - 保留 Phase 1 六个核心指标
    - issues 完全来自第二阶段步级诊断
    - 已去除旧版逐帧遗留分析逻辑
    """

    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def analyze_video(
        self,
        video_file,
        start_time: float = 0.0,
        end_time: Optional[float] = None,
        progress_callback=None,
    ) -> Dict[str, Any]:
        cap = None
        try:
            video_path = resolve_video_path(video_file)
            cap = cv2.VideoCapture(video_path)

            if not cap.isOpened():
                raise ValueError("无法打开视频文件，请确认视频路径和格式是否正确。")

            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            if fps <= 0:
                fps = 30.0

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            duration = total_frames / fps if fps > 0 else 0.0

            if end_time is None:
                end_time = duration

            start_time = float(start_time or 0.0)
            end_time = float(end_time or 0.0)

            if start_time < 0:
                raise ValueError("开始时间不能小于 0 秒。")
            if end_time <= start_time:
                raise ValueError("结束时间必须大于开始时间。")
            if (end_time - start_time) < 5.0:
                raise ValueError("分析时间段必须至少 5 秒。")
            if duration > 0 and start_time >= duration:
                raise ValueError("开始时间超过视频总时长。")
            if duration > 0 and end_time > duration:
                end_time = duration

            video_info = {
                "fps": float(fps),
                "total_frames": int(total_frames),
                "duration": float(duration),
                "start_time": float(start_time),
                "end_time": float(end_time),
                "analyzed_duration": float(end_time - start_time),
            }

            return self._process_video(
                cap=cap,
                video_info=video_info,
                start_time=start_time,
                end_time=end_time,
                progress_callback=progress_callback,
            )

        except Exception as e:
            print(f"[PoseAnalysisService] analyze_video 失败: {e}")
            traceback.print_exc()

            fallback_info = {
                "fps": 30.0,
                "total_frames": 0,
                "duration": 0.0,
                "start_time": float(start_time or 0.0),
                "end_time": float(end_time or 0.0) if end_time is not None else 0.0,
                "analyzed_duration": max(float((end_time or 0.0) - (start_time or 0.0)), 0.0),
            }
            data = generate_fallback_data(fallback_info)
            data["issues"].append(
                {
                    "type": "analysis_failed",
                    "severity": "high",
                    "message": f"分析失败：{str(e)}",
                    "suggestion": "请检查视频质量、拍摄角度和时间区间设置。",
                    "confidence": 1.0,
                    "phase": "global",
                    "evidence": {},
                    "step_ratio": None,
                    "supporting_step_indices": [],
                }
            )
            return data

        finally:
            if cap is not None:
                cap.release()

    def _process_video(
        self,
        cap: cv2.VideoCapture,
        video_info: Dict[str, Any],
        start_time: float,
        end_time: float,
        progress_callback=None,
    ) -> Dict[str, Any]:
        fps = float(video_info["fps"])
        start_frame = int(start_time * fps)
        end_frame = int(end_time * fps)

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        frames_data = []
        frame_idx = start_frame
        processed = 0
        total_to_process = max(end_frame - start_frame, 1)

        while cap.isOpened() and frame_idx < end_frame:
            success, frame = cap.read()
            if not success:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb)

            frame_time = frame_idx / fps
            frame_data = extract_frame_data(self.mp_pose, results, frame_idx, frame_time)
            frames_data.append(frame_data)

            processed += 1
            frame_idx += 1

            if progress_callback:
                progress = 5 + 75 * (processed / total_to_process)
                progress_callback(progress, f"正在分析视频帧：{processed}/{total_to_process}")

        if progress_callback:
            progress_callback(82, "正在构建时序信号")

        raw_series = build_raw_time_series(frames_data)
        inferred_fps = infer_fps_from_frames(frames_data)
        proc_series = preprocess_time_series(raw_series, inferred_fps)
        gait_events = detect_gait_events(proc_series, inferred_fps)

        step_records = build_step_records(
            proc_series=proc_series,
            gait_events=gait_events,
            timestamps=np.asarray(proc_series["timestamps"], dtype=float),
        )

        metrics = compute_phase1_metrics(proc_series, gait_events, inferred_fps)
        metrics["step_records"] = step_records

        if progress_callback:
            progress_callback(92, "正在生成第二阶段问题诊断")

        summary_issues = diagnose_phase2_issues(step_records, metrics)

        if progress_callback:
            progress_callback(100, "分析完成")

        return {
            "video_info": {
                **video_info,
                "analyzed_frames": int(len(frames_data)),
            },
            "frames": frames_data,
            "metrics": metrics,
            "issues": summary_issues,
        }

    def __del__(self):
        try:
            if hasattr(self, "pose") and self.pose is not None:
                self.pose.close()
        except Exception:
            pass
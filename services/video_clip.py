import os
import subprocess
import tempfile
from pathlib import Path


class VideoClipError(Exception):
    pass


def clip_video(input_path: str, start_time: float, end_time: float, output_dir: str) -> str:
    """
    使用 ffmpeg 将 input_path 裁剪为 [start_time, end_time] 片段，
    输出到 output_dir，返回输出文件绝对路径。
    """
    if not os.path.exists(input_path):
        raise VideoClipError(f"输入视频不存在: {input_path}")

    if start_time < 0:
        raise VideoClipError("开始时间不能小于 0")
    if end_time <= start_time:
        raise VideoClipError("结束时间必须大于开始时间")

    duration = end_time - start_time
    if duration < 5:
        raise VideoClipError("裁剪片段时长必须至少 5 秒")

    os.makedirs(output_dir, exist_ok=True)

    input_ext = Path(input_path).suffix.lower() or ".mp4"
    output_filename = f"clip_{next(tempfile._get_candidate_names())}{input_ext}"
    output_path = os.path.join(output_dir, output_filename)

    # 为了兼容性和精确裁剪，采用重新编码
    command = [
        "ffmpeg",
        "-y",
        "-ss", str(start_time),
        "-to", str(end_time),
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-movflags", "+faststart",
        output_path,
    ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
    except FileNotFoundError:
        raise VideoClipError("未检测到 ffmpeg，请先安装 ffmpeg 并加入系统 PATH")

    if result.returncode != 0:
        raise VideoClipError(f"视频裁剪失败: {result.stderr[:1000]}")

    if not os.path.exists(output_path):
        raise VideoClipError("裁剪输出文件未生成")

    return output_path
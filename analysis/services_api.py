import json
import os

from django.conf import settings
from django.core.files import File

from .models import VideoUpload, AnalysisResult
from services.pose_analysis import PoseAnalysisService
from services.video_clip import clip_video, VideoClipError


def make_json_safe(data, fallback=None):
    if fallback is None:
        fallback = {}
    try:
        json.dumps(data)
        return data
    except Exception:
        return fallback


def metric_value(metrics, key, default=None):
    item = metrics.get(key, default)
    if isinstance(item, dict):
        return item.get('value', default)
    return item


def process_video_upload(video_upload, original_start_time=0, original_end_time=None):
    original_file_path = video_upload.video_file.path

    clip_output_dir = os.path.join(settings.MEDIA_ROOT, 'videos')
    clipped_file_path = clip_video(
        input_path=original_file_path,
        start_time=original_start_time,
        end_time=original_end_time,
        output_dir=clip_output_dir,
    )

    with open(clipped_file_path, 'rb') as clipped_f:
        clipped_name = os.path.basename(clipped_file_path)

        old_name = video_upload.video_file.name if video_upload.video_file else None
        video_upload.video_file.save(clipped_name, File(clipped_f), save=False)

        if original_end_time is not None:
            clipped_duration = original_end_time - original_start_time
            video_upload.start_time = 0
            video_upload.end_time = clipped_duration

        video_upload.progress_message = '视频片段裁剪完成'
        video_upload.save()

        if old_name:
            old_abs_path = os.path.join(settings.MEDIA_ROOT, old_name)
            if os.path.exists(old_abs_path) and old_abs_path != video_upload.video_file.path:
                try:
                    os.remove(old_abs_path)
                except OSError:
                    pass

    if os.path.exists(clipped_file_path):
        try:
            os.remove(clipped_file_path)
        except OSError:
            pass

    analyzer = PoseAnalysisService()
    analysis_data = analyzer.analyze_video(
        video_upload.video_file,
        start_time=video_upload.start_time or 0,
        end_time=video_upload.end_time,
    )

    frames = make_json_safe(analysis_data.get('frames', []), fallback=[])
    issues = make_json_safe(analysis_data.get('issues', []), fallback=[])
    metrics = make_json_safe(analysis_data.get('metrics', {}), fallback={})
    video_info = analysis_data.get('video_info', {}) or {}

    AnalysisResult.objects.update_or_create(
        video=video_upload,
        defaults={
            'pose_data': frames,
            'issues': issues,
            'overall_metrics': metrics,
            'cadence': metric_value(metrics, 'cadence'),
            'stride_length': None,
            'ground_contact_time': metric_value(metrics, 'ground_contact_time'),
            'vertical_oscillation': metric_value(metrics, 'vertical_oscillation_rel'),
        }
    )

    video_upload.status = 'completed'
    video_upload.progress = 100
    video_upload.progress_message = '分析完成'
    video_upload.duration = video_info.get('duration')
    video_upload.frame_count = video_info.get('total_frames')
    video_upload.fps = video_info.get('fps')
    video_upload.error_message = ''
    video_upload.save()

    return video_upload
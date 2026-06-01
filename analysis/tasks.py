from celery import shared_task
from django.db import transaction

from .models import AnalysisResult, VideoUpload
from services.pose_analysis import PoseAnalysisService


def _safe_json_value(value, default):
    try:
        import json
        json.dumps(value)
        return value
    except Exception:
        return default


def _metric_value(metrics, key, default=None):
    item = (metrics or {}).get(key, default)
    if isinstance(item, dict):
        return item.get('value', default)
    return item


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 2})
def analyze_video_task(self, video_upload_id):
    video_upload = VideoUpload.objects.get(id=video_upload_id)

    def progress_callback(progress: float, message: str):
        video_upload.mark_processing(progress=int(progress), message=message)

    try:
        video_upload.mark_processing(progress=1, message='任务已启动')

        service = PoseAnalysisService()
        analysis_data = service.analyze_video(
            video_upload.video_file,
            start_time=video_upload.start_time or 0,
            end_time=video_upload.end_time,
            progress_callback=progress_callback,
        )

        frames = _safe_json_value(analysis_data.get('frames', []), [])
        issues = _safe_json_value(analysis_data.get('issues', []), [])
        metrics = _safe_json_value(analysis_data.get('metrics', {}), {})
        video_info = analysis_data.get('video_info', {}) or {}

        with transaction.atomic():
            result, _ = AnalysisResult.objects.update_or_create(
                video=video_upload,
                defaults={
                    'pose_data': frames,
                    'issues': issues,
                    'overall_metrics': metrics,
                    'cadence': _metric_value(metrics, 'cadence'),
                    'stride_length': _metric_value(metrics, 'stride_length'),
                    'ground_contact_time': _metric_value(metrics, 'ground_contact_time'),
                    'vertical_oscillation': _metric_value(metrics, 'vertical_oscillation_rel'),
                }
            )

            video_upload.mark_completed(
                duration=video_info.get('duration'),
                frame_count=video_info.get('total_frames'),
                fps=video_info.get('fps'),
            )

        return {
            'success': True,
            'video_upload_id': video_upload.id,
            'analysis_result_id': result.id,
        }

    except Exception as exc:
        video_upload.mark_failed(str(exc))
        raise
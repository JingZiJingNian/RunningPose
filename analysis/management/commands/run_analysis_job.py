import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from analysis.models import VideoUpload, AnalysisResult
from services.pose_analysis import PoseAnalysisService


def safe_json_value(value, default):
    try:
        json.dumps(value)
        return value
    except Exception:
        return default


def metric_value(metrics, key, default=None):
    item = (metrics or {}).get(key, default)
    if isinstance(item, dict):
        return item.get('value', default)
    return item


class Command(BaseCommand):
    help = 'Run analysis job for a VideoUpload in a standalone subprocess.'

    def add_arguments(self, parser):
        parser.add_argument('video_upload_id', type=int)

    def handle(self, *args, **options):
        video_upload_id = options['video_upload_id']

        try:
            video_upload = VideoUpload.objects.get(id=video_upload_id)
        except VideoUpload.DoesNotExist:
            raise CommandError(f'VideoUpload {video_upload_id} does not exist')

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

            frames = safe_json_value(analysis_data.get('frames', []), [])
            issues = safe_json_value(analysis_data.get('issues', []), [])
            metrics = safe_json_value(analysis_data.get('metrics', {}), {})
            video_info = analysis_data.get('video_info', {}) or {}

            with transaction.atomic():
                AnalysisResult.objects.update_or_create(
                    video=video_upload,
                    defaults={
                        'pose_data': frames,
                        'issues': issues,
                        'overall_metrics': metrics,
                        'cadence': metric_value(metrics, 'cadence'),
                        'stride_length': metric_value(metrics, 'stride_length'),
                        'ground_contact_time': metric_value(metrics, 'ground_contact_time'),
                        'vertical_oscillation': metric_value(metrics, 'vertical_oscillation_rel'),
                    }
                )

                video_upload.mark_completed(
                    duration=video_info.get('duration'),
                    frame_count=video_info.get('total_frames'),
                    fps=video_info.get('fps'),
                )

            self.stdout.write(self.style.SUCCESS(
                f'Analysis completed for VideoUpload {video_upload_id}'
            ))

        except Exception as exc:
            video_upload.mark_failed(str(exc))
            raise CommandError(f'Analysis failed for VideoUpload {video_upload_id}: {exc}')
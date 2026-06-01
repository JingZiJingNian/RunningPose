# history/management/commands/fix_history.py
from django.core.management.base import BaseCommand
from analysis.models import AnalysisResult, VideoUpload
from history.models import AnalysisHistory


class Command(BaseCommand):
    help = '修复历史记录，为所有已完成的分析创建历史记录'

    def handle(self, *args, **options):
        # 获取所有已完成的分析
        completed_videos = VideoUpload.objects.filter(status='completed')

        self.stdout.write(f"找到 {completed_videos.count()} 个已完成的视频")

        for video in completed_videos:
            # 检查是否已存在历史记录
            if not AnalysisHistory.objects.filter(video_upload=video).exists():
                try:
                    analysis_result = AnalysisResult.objects.get(video=video)
                    issues_count = len(analysis_result.issues) if analysis_result.issues else 0

                    history_record = AnalysisHistory.objects.create(
                        user=video.user,
                        video_upload=video,
                        title=video.title,
                        duration=video.duration or 0,
                        analyzed_frames=len(analysis_result.pose_data) if analysis_result.pose_data else 0,
                        issues_count=issues_count
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'创建历史记录: {history_record.title}')
                    )
                except AnalysisResult.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'视频 {video.title} 没有分析结果')
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(f'历史记录已存在: {video.title}')
                )
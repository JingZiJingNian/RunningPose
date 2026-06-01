# history/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from analysis.models import AnalysisResult, VideoUpload
from .models import AnalysisHistory


@receiver(post_save, sender=VideoUpload)
def handle_video_status_change(sender, instance, **kwargs):
    """处理视频状态变化"""
    if instance.status == 'completed':
        print(f"视频完成: {instance.title}")
        create_history_for_video(instance)


@receiver(post_save, sender=AnalysisResult)
def handle_analysis_result_creation(sender, instance, created, **kwargs):
    """处理分析结果创建"""
    if created:
        print(f"分析结果创建: {instance.video.title}, 状态: {instance.video.status}")
        # 检查视频是否已完成
        if instance.video.status == 'completed':
            create_history_for_video(instance.video)


def create_history_for_video(video):
    """为视频创建历史记录"""
    # 检查是否已存在历史记录
    if AnalysisHistory.objects.filter(video_upload=video).exists():
        print(f"历史记录已存在: {video.title}")
        return

    try:
        analysis_result = AnalysisResult.objects.get(video=video)
        print(f"为视频创建历史记录: {video.title}")

        # 计算问题数量
        issues_count = len(analysis_result.issues) if analysis_result.issues else 0

        # 创建历史记录
        history_record = AnalysisHistory.objects.create(
            user=video.user,
            video_upload=video,
            title=video.title,
            duration=video.duration or 0,
            analyzed_frames=len(analysis_result.pose_data) if analysis_result.pose_data else 0,
            issues_count=issues_count
        )
        print(f"历史记录创建成功: {history_record}")

    except AnalysisResult.DoesNotExist:
        print(f"视频 {video.title} 没有对应的分析结果")
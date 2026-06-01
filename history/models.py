from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse


class AnalysisHistory(models.Model):
    """分析历史记录 - 简化版本"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    video_upload = models.OneToOneField('analysis.VideoUpload', on_delete=models.CASCADE, verbose_name='视频上传记录')

    # 基本信息
    title = models.CharField(max_length=200, verbose_name='分析标题')
    analyzed_at = models.DateTimeField(auto_now_add=True, verbose_name='分析时间')
    duration = models.FloatField(verbose_name='视频时长(秒)')
    analyzed_frames = models.IntegerField(verbose_name='分析帧数')

    # 问题统计
    issues_count = models.IntegerField(default=0, verbose_name='问题数量')

    class Meta:
        verbose_name = '分析历史记录'
        verbose_name_plural = '分析历史记录'
        ordering = ['-analyzed_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"

    def get_absolute_url(self):
        return reverse('history:detail', kwargs={'result_id': self.video_upload_id})
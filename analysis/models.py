from django.db import models
from django.contrib.auth.models import User


class VideoUpload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    video_file = models.FileField(upload_to='videos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    duration = models.FloatField(null=True, blank=True)
    frame_count = models.IntegerField(null=True, blank=True)
    fps = models.FloatField(null=True, blank=True)

    start_time = models.FloatField(default=0, help_text="分析开始时间（秒）")
    end_time = models.FloatField(null=True, blank=True, help_text="分析结束时间（秒）")

    progress = models.PositiveSmallIntegerField(default=0)
    progress_message = models.CharField(max_length=255, blank=True, default='')
    error_message = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"

    def mark_processing(self, progress=None, message=''):
        self.status = 'processing'

        update_fields = ['status']

        if progress is not None:
            self.progress = max(0, min(100, int(progress)))
            update_fields.append('progress')

        if message is not None:
            self.progress_message = message[:255]
            update_fields.append('progress_message')

        self.save(update_fields=update_fields)

    def mark_completed(self, duration=None, frame_count=None, fps=None):
        self.status = 'completed'
        self.progress = 100
        self.progress_message = '分析完成'
        self.error_message = ''

        self.duration = duration
        self.frame_count = frame_count
        self.fps = fps

        self.save(update_fields=[
            'status',
            'progress',
            'progress_message',
            'error_message',
            'duration',
            'frame_count',
            'fps',
        ])

    def mark_failed(self, error_message=''):
        self.status = 'failed'
        self.progress_message = '分析失败'
        self.error_message = (error_message or '')[:5000]
        self.save(update_fields=['status', 'progress_message', 'error_message'])


class AnalysisResult(models.Model):
    video = models.OneToOneField(VideoUpload, on_delete=models.CASCADE, related_name='analysis_result')

    pose_data = models.JSONField(null=True, blank=True)
    mesh_data = models.JSONField(null=True, blank=True)
    analysis_image = models.ImageField(upload_to='analysis_results/', null=True, blank=True)

    cadence = models.FloatField(null=True, blank=True)
    stride_length = models.FloatField(null=True, blank=True)
    ground_contact_time = models.FloatField(null=True, blank=True)
    vertical_oscillation = models.FloatField(null=True, blank=True)

    issues = models.JSONField(null=True, blank=True)
    overall_metrics = models.JSONField(null=True, blank=True)

    analyzed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-analyzed_at']

    def __str__(self):
        return f"分析结果 - {self.video.title}"

    def get_issues_count(self):
        return len(self.issues or [])

    def get_severity_level(self):
        if not self.issues:
            return 'excellent'

        severe_count = sum(1 for issue in self.issues if issue.get('severity') == 'high')
        if severe_count > 0:
            return 'poor'
        elif len(self.issues) > 2:
            return 'fair'
        return 'good'
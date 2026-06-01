from rest_framework import serializers

from .models import AnalysisHistory
from analysis.models import AnalysisResult


def metric_value(metrics, key, default=None):
    item = (metrics or {}).get(key, default)
    if isinstance(item, dict):
        return item.get('value', default)
    return item


class HistoryListSerializer(serializers.ModelSerializer):
    video_upload_id = serializers.IntegerField(source='video_upload.id', read_only=True)
    status = serializers.CharField(source='video_upload.status', read_only=True)
    uploaded_at = serializers.DateTimeField(source='video_upload.uploaded_at', read_only=True)

    class Meta:
        model = AnalysisHistory
        fields = [
            'video_upload_id',
            'title',
            'analyzed_at',
            'uploaded_at',
            'duration',
            'analyzed_frames',
            'issues_count',
            'status',
        ]


class HistoryDetailSerializer(serializers.ModelSerializer):
    video_upload_id = serializers.IntegerField(source='video_upload.id', read_only=True)
    status = serializers.CharField(source='video_upload.status', read_only=True)
    progress = serializers.IntegerField(source='video_upload.progress', read_only=True)
    progress_message = serializers.CharField(source='video_upload.progress_message', read_only=True)
    error_message = serializers.CharField(source='video_upload.error_message', read_only=True)
    summary = serializers.SerializerMethodField()
    issues = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisHistory
        fields = [
            'video_upload_id',
            'title',
            'analyzed_at',
            'duration',
            'analyzed_frames',
            'issues_count',
            'status',
            'progress',
            'progress_message',
            'error_message',
            'summary',
            'issues',
        ]

    def _get_result(self, obj):
        try:
            return obj.video_upload.analysis_result
        except AnalysisResult.DoesNotExist:
            return None

    def get_summary(self, obj):
        result = self._get_result(obj)
        metrics = result.overall_metrics if result else {}
        return {
            'cadence': metric_value(metrics, 'cadence'),
            'ground_contact_time': metric_value(metrics, 'ground_contact_time'),
            'flight_time': metric_value(metrics, 'flight_time'),
            'vertical_oscillation_rel': metric_value(metrics, 'vertical_oscillation_rel'),
            'trunk_lean_angle': metric_value(metrics, 'trunk_lean_angle'),
            'overstride_index': metric_value(metrics, 'overstride_index'),
        }

    def get_issues(self, obj):
        result = self._get_result(obj)
        return result.issues if result else []
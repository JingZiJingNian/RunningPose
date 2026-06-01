from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import AnalysisHistory
from analysis.models import VideoUpload, AnalysisResult


def _metric_value(metrics, key, default=None):
    item = (metrics or {}).get(key, default)
    if isinstance(item, dict):
        return item.get('value', default)
    return item


@login_required
def history_list(request):
    analyses = AnalysisHistory.objects.filter(user=request.user).select_related('video_upload')

    total_count = analyses.count()
    with_issues_count = analyses.filter(issues_count__gt=0).count()
    clean_count = total_count - with_issues_count

    latest_analysis = analyses.first()

    context = {
        'analyses': analyses,
        'total_count': total_count,
        'with_issues_count': with_issues_count,
        'clean_count': clean_count,
        'latest_analysis': latest_analysis,
    }
    return render(request, 'history/list.html', context)


@login_required
def history_detail(request, result_id):
    analysis = get_object_or_404(
        AnalysisHistory,
        video_upload_id=result_id,
        user=request.user
    )

    video_upload = get_object_or_404(VideoUpload, id=result_id, user=request.user)

    try:
        analysis_result = AnalysisResult.objects.get(video=video_upload)
        pose_data_json = analysis_result.pose_data if analysis_result.pose_data else []
        metrics = analysis_result.overall_metrics or {}
        issues = analysis_result.issues or []
    except AnalysisResult.DoesNotExist:
        analysis_result = None
        pose_data_json = []
        metrics = {}
        issues = []

    context = {
        'analysis': analysis,
        'video_upload': video_upload,
        'analysis_result': analysis_result,
        'pose_data_json': pose_data_json,
        'metrics': metrics,
        'issues': issues,
        'cadence_value': _metric_value(metrics, 'cadence'),
        'gct_value': _metric_value(metrics, 'ground_contact_time'),
        'flight_value': _metric_value(metrics, 'flight_time'),
        'vo_value': _metric_value(metrics, 'vertical_oscillation_rel'),
        'trunk_value': _metric_value(metrics, 'trunk_lean_angle'),
        'osi_value': _metric_value(metrics, 'overstride_index'),
    }

    return render(request, 'history/detail.html', context)


@login_required
def delete_analysis(request, result_id):
    analysis = get_object_or_404(AnalysisHistory, video_upload_id=result_id, user=request.user)

    if request.method == 'POST':
        title = analysis.title
        analysis.delete()
        messages.success(request, f'分析记录 “{title}” 已删除')
        return redirect('history:list')

    return redirect('history:detail', result_id=result_id)
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from analysis.models import VideoUpload, AnalysisResult
from history.models import AnalysisHistory


def home(request):
    """首页视图"""
    context = {
        'title': '跑步姿态分析系统',
        'welcome_message': '欢迎使用专业的跑步姿态分析系统'
    }
    return render(request, 'main/home.html', context)


def about(request):
    """关于页面"""
    context = {
        'title': '关于 GaitFix',
        'feature_count': 6,
        'report_modules': 4,
    }
    return render(request, 'main/about.html', context)


@login_required
def dashboard(request):
    """用户分析中心"""
    uploads = VideoUpload.objects.filter(user=request.user).order_by('-uploaded_at')
    histories = AnalysisHistory.objects.filter(user=request.user).select_related('video_upload').order_by('-analyzed_at')

    total_analyses = uploads.count()
    completed_analyses = uploads.filter(status='completed').count()
    processing_analyses = uploads.filter(status__in=['pending', 'processing']).count()
    failed_analyses = uploads.filter(status='failed').count()

    total_issue_records = histories.filter(issues_count__gt=0).count()
    stable_records = histories.filter(issues_count=0).count()

    latest_history = histories.first()
    recent_histories = histories[:5]

    avg_issues = 0
    if histories.exists():
        avg_issues = round(sum(item.issues_count for item in histories) / histories.count(), 2)

    latest_result = None
    latest_metrics = {}
    if latest_history:
        try:
            latest_result = AnalysisResult.objects.get(video=latest_history.video_upload)
            latest_metrics = latest_result.overall_metrics or {}
        except AnalysisResult.DoesNotExist:
            latest_result = None
            latest_metrics = {}

    context = {
        'title': '分析中心',
        'total_analyses': total_analyses,
        'completed_analyses': completed_analyses,
        'processing_analyses': processing_analyses,
        'failed_analyses': failed_analyses,
        'total_issue_records': total_issue_records,
        'stable_records': stable_records,
        'avg_issues': avg_issues,
        'latest_history': latest_history,
        'recent_histories': recent_histories,
        'latest_metrics': latest_metrics,
        'latest_result': latest_result,
    }
    return render(request, 'main/dashboard.html', context)


def article_running_posture(request):
    return render(request, 'main/article_running_posture.html')


def article_injury_prevention(request):
    return render(request, 'main/article_injury_prevention.html')


def article_training_plan(request):
    return render(request, 'main/article_training_plan.html')
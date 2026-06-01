import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files import File
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .executors import schedule_analysis
from .forms import VideoUploadForm
from .models import AnalysisResult, VideoUpload
from services.video_clip import VideoClipError, clip_video


@login_required
def video_upload(request):
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)

        if form.is_valid():
            original_start_time = float(form.cleaned_data.get('start_time') or 0)
            original_end_time = form.cleaned_data.get('end_time')
            if original_end_time is not None:
                original_end_time = float(original_end_time)

            video_upload = form.save(commit=False)
            video_upload.user = request.user
            video_upload.status = 'processing'
            video_upload.progress = 0
            video_upload.progress_message = '开始处理视频'
            video_upload.error_message = ''
            video_upload.save()

            original_file_path = video_upload.video_file.path

            try:
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
                    else:
                        video_upload.start_time = 0

                    video_upload.progress = 1
                    video_upload.progress_message = '视频片段裁剪完成，等待后台分析'
                    video_upload.error_message = ''
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

                schedule_analysis(video_upload.id)

                messages.success(request, '视频上传成功，后台正在分析中。')
                return redirect('analysis:results', result_id=video_upload.id)

            except VideoClipError as exc:
                video_upload.status = 'failed'
                video_upload.progress_message = '视频裁剪失败'
                video_upload.error_message = str(exc)[:5000]
                video_upload.save()

                messages.error(request, f'视频裁剪失败：{exc}')

            except Exception as exc:
                video_upload.status = 'failed'
                video_upload.progress_message = '任务创建失败'
                video_upload.error_message = str(exc)[:5000]
                video_upload.save()

                messages.error(request, f'任务创建失败：{exc}')
        else:
            messages.error(request, '表单验证失败，请检查输入。')
    else:
        form = VideoUploadForm()

    return render(request, 'analysis/upload.html', {'form': form})


@login_required
def analysis_results(request, result_id):
    video_upload = get_object_or_404(VideoUpload, id=result_id, user=request.user)

    try:
        analysis_result = video_upload.analysis_result
    except AnalysisResult.DoesNotExist:
        analysis_result = None

    context = {
        'video_upload': video_upload,
        'analysis_result': analysis_result,
        'pose_data_json': analysis_result.pose_data if analysis_result and analysis_result.pose_data else [],
        'error_message': video_upload.error_message,
    }
    return render(request, 'analysis/results.html', context)


@login_required
def analysis_progress(request, video_id):
    video_upload = get_object_or_404(VideoUpload, id=video_id, user=request.user)

    return JsonResponse({
        'status': video_upload.status,
        'progress': video_upload.progress,
        'message': video_upload.progress_message,
        'error_message': video_upload.error_message,
        'has_result': hasattr(video_upload, 'analysis_result'),
    })
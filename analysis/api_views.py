import os

from django.conf import settings
from django.core.files import File
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .executors import schedule_analysis
from .models import VideoUpload
from .serializers import (
    VideoUploadCreateSerializer,
    VideoUploadStatusSerializer,
    AnalysisResultSerializer,
)
from services.video_clip import clip_video, VideoClipError


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def api_upload_video(request):
    serializer = VideoUploadCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    original_start_time = float(serializer.validated_data.get('start_time') or 0)
    original_end_time = serializer.validated_data.get('end_time')
    if original_end_time is not None:
        original_end_time = float(original_end_time)

    video_upload = serializer.save(
        user=request.user,
        status='processing',
        progress=0,
        progress_message='开始处理视频',
        error_message='',
    )

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

        return Response({
            'analysis_id': video_upload.id,
            'status': video_upload.status,
            'progress': video_upload.progress,
            'message': video_upload.progress_message,
        }, status=status.HTTP_201_CREATED)

    except VideoClipError as exc:
        video_upload.mark_failed(str(exc))
        return Response({
            'analysis_id': video_upload.id,
            'status': 'failed',
            'message': '视频裁剪失败',
            'error_message': video_upload.error_message,
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as exc:
        video_upload.mark_failed(str(exc))
        return Response({
            'analysis_id': video_upload.id,
            'status': 'failed',
            'message': '任务创建失败',
            'error_message': video_upload.error_message,
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_upload_status(request, upload_id):
    video_upload = get_object_or_404(VideoUpload, id=upload_id, user=request.user)
    serializer = VideoUploadStatusSerializer(video_upload)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_upload_result(request, upload_id):
    video_upload = get_object_or_404(VideoUpload, id=upload_id, user=request.user)

    if not hasattr(video_upload, 'analysis_result'):
        return Response({
            'analysis_id': video_upload.id,
            'status': video_upload.status,
            'progress': video_upload.progress,
            'message': video_upload.progress_message,
            'error_message': video_upload.error_message,
        }, status=status.HTTP_404_NOT_FOUND)

    serializer = AnalysisResultSerializer(
        video_upload.analysis_result,
        context={'request': request}
    )
    return Response(serializer.data)
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AnalysisHistory
from .serializers import HistoryListSerializer, HistoryDetailSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_history_list(request):
    queryset = (
        AnalysisHistory.objects
        .filter(user=request.user)
        .select_related('video_upload')
        .order_by('-analyzed_at')
    )
    serializer = HistoryListSerializer(queryset, many=True)
    return Response({
        'count': queryset.count(),
        'results': serializer.data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_history_detail(request, video_upload_id):
    item = get_object_or_404(
        AnalysisHistory.objects.select_related('video_upload'),
        user=request.user,
        video_upload_id=video_upload_id
    )
    serializer = HistoryDetailSerializer(item)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def api_history_delete(request, video_upload_id):
    item = get_object_or_404(
        AnalysisHistory,
        user=request.user,
        video_upload_id=video_upload_id
    )
    item.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
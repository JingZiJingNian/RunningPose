from django.urls import path
from . import api_views

urlpatterns = [
    path('upload/', api_views.api_upload_video, name='api_upload_video'),
    path('uploads/<int:upload_id>/status/', api_views.api_upload_status, name='api_upload_status'),
    path('uploads/<int:upload_id>/result/', api_views.api_upload_result, name='api_upload_result'),
]
from django.urls import path
from . import api_views

urlpatterns = [
    path('', api_views.api_history_list, name='api_history_list'),
    path('<int:video_upload_id>/', api_views.api_history_detail, name='api_history_detail'),
    path('<int:video_upload_id>/delete/', api_views.api_history_delete, name='api_history_delete'),
]
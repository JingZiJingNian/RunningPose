from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    path('upload/', views.video_upload, name='upload'),
    path('results/<int:result_id>/', views.analysis_results, name='results'),
    path('progress/<int:video_id>/', views.analysis_progress, name='progress'),
]
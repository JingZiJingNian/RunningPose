from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('dashboard/', views.dashboard, name='dashboard'),

    path('articles/running-posture/', views.article_running_posture, name='article_running_posture'),
    path('articles/injury-prevention/', views.article_injury_prevention, name='article_injury_prevention'),
    path('articles/training-plan/', views.article_training_plan, name='article_training_plan'),
]
from django.urls import path
from . import views

app_name = 'history'

urlpatterns = [
    path('', views.history_list, name='list'),
    path('<int:result_id>/', views.history_detail, name='detail'),
    path('<int:result_id>/delete/', views.delete_analysis, name='delete'),
]
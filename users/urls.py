from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('security/', views.security_settings, name='security_settings'),
    path('delete-avatar/', views.delete_avatar, name='delete_avatar'),
    path('login-history/', views.login_history, name='login_history'),
    path('logout/done/', views.logout_done, name='logout_done'),
]
# RunningPose/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    path('analysis/', include('analysis.urls')),
    path('history/', include('history.urls')),
    path('users/', include('users.urls')),
    path('oauth/', include('social_django.urls', namespace='social')),  # 社交登录URL
    path('api/', include('RunningPose.api_urls')),
]

# 开发环境下的媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
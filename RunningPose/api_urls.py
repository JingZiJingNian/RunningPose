from django.urls import include, path

urlpatterns = [
    path('analysis/', include('analysis.api_urls')),
    path('users/', include('users.api_urls')),
    path('history/', include('history.api_urls')),
]
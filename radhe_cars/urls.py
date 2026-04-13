from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from radhe_cars import views as project_views

urlpatterns = [
    path('health/', project_views.health, name='health'),
    path('admin/', admin.site.urls),
    path('admin-panel/', include('cars.admin_panel.urls')),
    path('accounts/', include('allauth.urls')),
    path('', include('cars.urls')),
]

# Dev only: WhiteNoise serves static in production. Nginx should serve MEDIA_ROOT at MEDIA_URL.
if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

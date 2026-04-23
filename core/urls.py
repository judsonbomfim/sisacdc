from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.conf import settings
from django.conf.urls.static import static
from apps.dashboard.views import index, clear_cache


def health_check(request):
    return HttpResponse("ok", status=200)


urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('', index, name='dashboard'),
    path('admin/', admin.site.urls),
    path('pedidos/', include('apps.orders.urls')),
    path('sims/', include('apps.sims.urls')),
    path('', include('apps.users.urls')),
    path('email/', include('apps.send_email.urls')),
    path('voz/', include('apps.voice_calls.urls')),
    path('clear_cache/', clear_cache, name='clear_cache'),
    
    # API URLs
    path('api/', include('rest_framework.urls')),  # Interface de navegação do DRF (opcional)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # Obter token
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Renovar token   
    path('api/sims/', include('apps.sims.urls_api')),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
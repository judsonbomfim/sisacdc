from django.urls import path
from .views.api import ConsumoView

urlpatterns = [
    path('consumo/<str:iccid>/', ConsumoView.as_view(), name='consumo'),
]
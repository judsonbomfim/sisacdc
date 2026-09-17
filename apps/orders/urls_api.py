from django.urls import path

from .views_webhook import DataAtivacaoEventView

urlpatterns = [
    path(
        'events/data-ativacao/',
        DataAtivacaoEventView.as_view(),
        name='orders_webhook_data_ativacao',
    ),
    path(
        'events/data-ativacao',
        DataAtivacaoEventView.as_view(),
        name='orders_webhook_data_ativacao_noslash',
    ),
]

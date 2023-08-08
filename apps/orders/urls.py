from django.urls import path
from apps.orders.views import orders_list, ord_import, ord_edit, ord_actions, ord_filters_st

urlpatterns = [
    path('listar/', orders_list, name='orders_list'),
    path('importar/', ord_import, name='ord_import'),
    path('editar/<int:id>', ord_edit, name='ord_edit'),
    path('acoes/', ord_actions, name='ord_actions'),
    path('filtro/<str:filter>', ord_filters_st, name='ord_filters_st'),
]
from django.urls import path
from apps.orders.views import orders_list, ord_update, ord_edit

urlpatterns = [
    path('listar/', orders_list, name='orders_list'),
    path('atualizar/', ord_update, name='ord_update'),
    path('editar/<int:id>', ord_edit, name='ord_edit'),
    # path('lista/<int:id>', orders, name='orders_list_id'),
    # path('detalhes/<int:id>', order_det, name='order_details'),
]
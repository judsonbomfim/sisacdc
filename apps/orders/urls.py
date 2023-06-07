from django.urls import path
from apps.orders.views import orders_list, ord_update

urlpatterns = [
    path('lista/', orders_list, name='orders_list'),
    # path('lista/<int:id>', orders, name='orders_list_id'),
    # path('detalhes/<int:id>', order_det, name='order_details'),
    path('update/', ord_update, name='ord_update'),
]
from django.urls import path
from apps.orders.views import orders_list, ord_import, ord_edit, ord_export_op, orders_del_man

urlpatterns = [
    path('listar/', orders_list, name='orders_list'),
    path('importar/', ord_import, name='ord_import'),
    path('editar/<int:id>', ord_edit, name='ord_edit'),
    path('exportar/', ord_export_op, name='ord_export_op'),
    path('del_ord/', orders_del_man, name='orders_del_man'),
]
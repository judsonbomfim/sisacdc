from django.urls import path
from . import views

urlpatterns = [
    path('listar/', views.orders_list, name='orders_list'),
    path('detalhes/<int:order_id>', views.ord_details, name='ord_details'),
    path('importar/', views.ord_import, name='ord_import'),
    path('editar/<int:id>', views.ord_edit, name='ord_edit'),
    path('exportar/', views.ord_export_op, name='ord_export_op'),
    path('exportar/clientes/', views.exportClient, name='export_client'),
    path('exportar/clientes/progresso/', views.export_client_progress, name='export_client_progress'),
    path('exportar/clientes/download/', views.export_client_download, name='export_client_download'),
    # path('exportar/protocolo-csv', views.export_protocolo_from_txt, name='export_protocolo_from_txt'),  # View não existe
    path('enviar/esims/', views.send_esims, name='send_esims'),
    path('ativacoes/', views.orders_activations, name='orders_activations'),
    path('ativacoes/exportar', views.ord_export, name='ord_export'),
]
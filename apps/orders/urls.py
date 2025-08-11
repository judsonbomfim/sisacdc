from django.urls import path
from . import views

urlpatterns = [
    path('listar/', views.orders_list, name='orders_list'),
    path('detalhes/<int:order_id>', views.ord_details, name='ord_details'),
    path('importar/', views.ord_import, name='ord_import'),
    path('editar/<int:id>', views.ord_edit, name='ord_edit'),
    path('exportar/', views.ord_export_op, name='ord_export_op'),
    path('enviar/esims/', views.send_esims, name='send_esims'),
    path('ativacoes/', views.orders_activations, name='orders_activations'),
    path('ativacoes/exportar', views.ord_export_act, name='ord_export_act'),
    path('atualizar_status', views.atualizar_status, name='atualizar_status'),
    path('teste_api', views.testeAPI, name='teste_api'),
    path('alterar_operadora', views.alterarOperadora, name='alterar_operadora'),
    # path('texto/', views.textImg, name='text_img'),
    # path('esimstore/', views.esimExpSis, name='esimstore'),
]
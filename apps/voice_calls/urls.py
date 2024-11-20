from django.urls import path
from . import views

urlpatterns = [
    path('listar/', views.voice_index, name='voice_index'),
    path('listar/numeros/', views.mumber_list, name='mumber_list'),
    path('importar/', views.voice_import, name='voice_import'),
    path('editar/<int:id>', views.voice_edit, name='voice_edit'),
    path('up_pass/<int:id>', views.up_password, name='up_password'),
]
from django.urls import path
from . import views

urlpatterns = [
    path('listar/', views.voice_index, name='voice_index'),
    path('importar/', views.voice_import, name='voice_import'),
    path('editar/<int:id>', views.voice_edit, name='voice_edit'),
]
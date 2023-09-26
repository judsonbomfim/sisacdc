from django.urls import path
from . import views

urlpatterns = [
    path('enviar/', views.send_email, name='send_email'),
    path('enviar/<int:id>', views.send_email, name='resend_email'),
]
from django.urls import path
from . import views

urlpatterns = [
    # path('enviar/', views.SendEmail.send_email, name=''),
    path('enviar/<int:id>', views.SendEmail.send_email, name='send_email'),
    path('enviar_esims', views.SendEmail.send_email_esims, name='send_email_esims'),
]
from django.urls import path
from . import views

urlpatterns = [
    # path('enviar/', views.SendEmail.send_email, name=''),
    path('enviar/<int:id>', views.send_email, name='send_email'),
    path('enviar_esims', views.send_email_esims, name='send_email_esims'),
    path('enviar_voice/<int:id>', views.send_email_voices, name='send_email_voices'),
    path('esim-link/<str:platform>', views.esim_install_redirect, name='esim_install_redirect'),
]
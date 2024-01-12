from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.models import User
from .classes import SendEmail
from apps.orders.models import Orders, Notes
from apps.send_email.tasks import send_esims
    
def send_email(request,id):
    send_esims.delay(id=id)      
    messages.success(request,f'E-mail enviado com sucesso!!')
    add_sim = Notes( 
        id_item = Orders.objects.get(pk=id),
        id_user = User.objects.get(pk=request.user.id),
        note = 'E-mail enviado com sucesso!',
        type_note = 'S',
    )
    add_sim.save()
    return redirect('orders_list')
    
def send_email_esims():
    send_esims.delay(id=None)
    return redirect('send_esims')
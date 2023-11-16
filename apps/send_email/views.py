from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.models import User
from .classes import SendEmail
from apps.orders.models import Orders, Notes
    
def send_email(request,id):
    SendEmail.mailAction(id=id)      
    messages.success(request,f'E-mail enviado com sucesso!!')
    add_sim = Notes( 
        id_item = Orders.objects.get(pk=id),
        id_user = User.objects.get(pk=request.user.id),
        note = 'E-mail enviado com sucesso!',
        type_note = 'S',
    )
    add_sim.save()
    return redirect('orders_list')
    
def send_email_esims(request):
    id_user = User.objects.get(pk=request.user.id)
    SendEmail.mailAction(request=request,id_user=id_user)
    return redirect('send_esims')
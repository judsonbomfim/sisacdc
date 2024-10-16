from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.send_email.tasks import send_email_sims, send_email_voice

@login_required(login_url='/login/')
def send_email(request,id):
    send_email_sims.delay(id=id)    
    messages.success(request,f'E-mail enviado com sucesso!!')
    return redirect('orders_list')    

@login_required(login_url='/login/')
def send_email_esims():
    send_email_sims.delay()
    # return redirect('send_esims')
    
@login_required(login_url='/login/')
def send_email_voices(request,id):
    send_email_voice.delay(id=id)
    messages.success(request,f'E-mail enviado com sucesso!!')
    return redirect('voice_index')
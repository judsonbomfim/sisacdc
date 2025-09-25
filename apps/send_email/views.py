from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.send_email.tasks import send_email_sims, send_email_voice
from apps.voice_calls.classes import NoteVoiceCall
from apps.voice_calls.models import VoiceCalls

@login_required(login_url='/login/')
def send_email(request,id):
    send_email_sims.delay(id=id)    
    return redirect('orders_list')    

@login_required(login_url='/login/')
def send_email_esims():
    send_email_sims.delay()
    # return redirect('send_esims')
    
@login_required(login_url='/login/')
def send_email_voices(request,id):
    send_email_voice.delay(id=id)
    voz = VoiceCalls.objects.get(id=id)    
    NoteVoiceCall.addNote(id_item=voz, note="Pedido Alterado", id_user=request.user, type_note='P')
    return redirect('voice_index')
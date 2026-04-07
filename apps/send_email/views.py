from urllib.parse import quote
from django.conf import settings
from django.http import HttpResponseBadRequest
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
    NoteVoiceCall.addNote(id_item=voz, note="E-mail enviado!", type_note='S')
    return redirect('voice_index')


def esim_install_redirect(request, platform):
    lpa = (request.GET.get('lpa') or '').strip()
    if not lpa:
        return HttpResponseBadRequest('LPA ausente.')

    if platform == 'ios':
        base_url = settings.LINK_ESIM_IOS
    elif platform == 'android':
        base_url = settings.LINK_ESIM_ANDROID
    else:
        return HttpResponseBadRequest('Plataforma invalida.')

    return redirect(f'{base_url}{quote(lpa, safe="")}')
import os
import time
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlencode
from apps.voice_calls.classes import NoteVoiceCall, UpdateVoice
from apps.voice_calls.models import VoiceNumbers, VoiceCalls
from apps.voice_calls.tasks import number_up_status, voiceActivate, voiceDesactivate, voices_up_status, update_password
from apps.orders.models import Orders
from apps.orders.classes import DateFormats
import pandas as pd
import logging
logger = logging.getLogger(__name__)


def _voice_list_params(request):
    """Lê filtros da listagem de voz (GET/POST)."""
    src = request.POST if request.method == 'POST' else request.GET
    params = {
        'voice_item_f': (src.get('voice_item_f') or '').strip(),
        'voice_number_f': (src.get('voice_number_f') or '').strip(),
        'voice_status_f': (src.get('voice_status_f') or '').strip(),
        'voice_going_1': (src.get('voice_going_1') or '').strip(),
        'voice_going_2': (src.get('voice_going_2') or '').strip(),
        'voice_return_1': (src.get('voice_return_1') or '').strip(),
        'voice_return_2': (src.get('voice_return_2') or '').strip(),
    }

    # Intervalo textual (flatpickr / datepicker): "dd/mm/yyyy - dd/mm/yyyy"
    voice_going_f = (src.get('voice_going_f') or '').strip()
    if voice_going_f and not params['voice_going_1']:
        parts = [item.strip() for item in voice_going_f.split('-')]
        params['voice_going_1'] = DateFormats.dateF(parts[0])
        if len(parts) > 1 and parts[1]:
            try:
                params['voice_going_2'] = DateFormats.dateF(parts[1])
            except Exception:
                params['voice_going_2'] = ''

    voice_return_f = (src.get('voice_return_f') or '').strip()
    if voice_return_f and not params['voice_return_1']:
        parts = [item.strip() for item in voice_return_f.split('-')]
        params['voice_return_1'] = DateFormats.dateF(parts[0])
        if len(parts) > 1 and parts[1]:
            try:
                params['voice_return_2'] = DateFormats.dateF(parts[1])
            except Exception:
                params['voice_return_2'] = ''

    return params


def _voice_list_url_filter(params):
    query = {}
    for key in (
        'voice_item_f',
        'voice_number_f',
        'voice_status_f',
        'voice_going_1',
        'voice_going_2',
        'voice_return_1',
        'voice_return_2',
    ):
        if params.get(key):
            query[key] = params[key]
    return f'&{urlencode(query)}' if query else ''


def _voice_list_redirect(params=None):
    url = reverse('voice_index')
    if not params:
        return redirect(url)
    query = _voice_list_url_filter(params)
    return redirect(f'{url}?{query[1:]}' if query else url)


@login_required(login_url='/login/')
def voice_index(request):
    url_cdn = settings.URL_CDN
    params = _voice_list_params(request)

    if request.method == 'POST' and 'up_status' in request.POST:
        voice_id = request.POST.getlist('voice_id')
        voice_st = request.POST.get('voice_st')
        if voice_id and voice_st:
            if voice_st == 'AT':
                voiceActivate.delay(id=voice_id)
            elif voice_st == 'DS':
                voiceDesactivate.delay(id=voice_id)
            time.sleep(5)
            voices_up_status.delay(voice_id, voice_st)
            messages.success(request, 'Pedido(s) atualizado com sucesso!')
        else:
            messages.info(request, 'Você precisa marcar alguma opção')
        return _voice_list_redirect(params)

    fields_df = [
        'id', 'id_number__number', 'id_item__client', 'id_number__id', 'id_item__item_id',
        'id_number__login', 'id_number__password', 'id_number__number_qrcode',
        'days', 'activation_date', 'call_status',
    ]

    voices_all = VoiceCalls.objects.all().order_by('-id')
    vox_status = VoiceCalls.call_status.field.choices
    vox_status_dict = dict(vox_status)

    voices_df = pd.DataFrame(voices_all.values(*fields_df))
    voices_df = voices_df.rename(columns={
        'id_item__item_id': 'order_id',
        'id_number__id': 'number_id',
        'id_item__client': 'client',
        'id_number__number': 'num_number',
        'id_number__login': 'num_login',
        'id_number__password': 'num_password',
        'id_number__number_qrcode': 'num_qrcode',
    })
    if not voices_df.empty:
        voices_df['activation_date'] = pd.to_datetime(voices_df['activation_date'])
        voices_df['return_date'] = (
            voices_df['activation_date']
            + pd.to_timedelta(voices_df['days'], unit='d')
            - pd.to_timedelta(1, unit='d')
        )
        voices_df['call_status'] = voices_df['call_status'].map(vox_status_dict)
        voices_df['num_number'] = voices_df['num_number'].fillna(0).astype(int)
        voices_df['number_id'] = voices_df['number_id'].fillna(0).astype(int)

    voices_l = voices_df
    voice_item_f = params['voice_item_f']
    voice_number_f = params['voice_number_f']
    voice_status_f = params['voice_status_f']
    voice_going_1 = params['voice_going_1']
    voice_going_2 = params['voice_going_2']
    voice_return_1 = params['voice_return_1']
    voice_return_2 = params['voice_return_2']

    if voice_item_f:
        voices_l = voices_l[voices_l['order_id'].astype(str).str.contains(str(voice_item_f))]

    if voice_number_f:
        try:
            voice_number_int = int(voice_number_f)
            voices_l = voices_l[voices_l['num_number'] == voice_number_int]
        except (TypeError, ValueError):
            voices_l = voices_l.iloc[0:0]

    if voice_going_1 and voice_going_2:
        voices_l = voices_l[
            (voices_l['activation_date'] >= voice_going_1)
            & (voices_l['activation_date'] <= voice_going_2)
        ]
    elif voice_going_1:
        voices_l = voices_l[voices_l['activation_date'] == voice_going_1]

    if voice_return_1 and voice_return_2:
        voices_l = voices_l[
            (voices_l['return_date'] >= voice_return_1)
            & (voices_l['return_date'] <= voice_return_2)
        ]
    elif voice_return_1:
        voices_l = voices_l[voices_l['return_date'] == voice_return_1]

    if voice_status_f:
        voices_l = voices_l[voices_l['call_status'] == voice_status_f]

    url_filter = _voice_list_url_filter(params)
    voice_count = int(voices_l.shape[0])
    voices_l = voices_l.to_dict('records')

    vox_st_list = [
        (code, label, voices_all.filter(call_status=code).count())
        for code, label in vox_status
    ]

    paginator = Paginator(voices_l, 50)
    voices = paginator.get_page(request.GET.get('page'))

    context = {
        'voices': voices,
        'vox_status': vox_status,
        'vox_st_list': vox_st_list,
        'url_cdn': url_cdn,
        'url_filter': url_filter,
        'voice_count': voice_count,
        'voice_item_f': voice_item_f,
        'voice_number_f': voice_number_f,
        'voice_status_f': voice_status_f,
        'voice_going_1': voice_going_1,
        'voice_going_2': voice_going_2,
        'voice_return_1': voice_return_1,
        'voice_return_2': voice_return_2,
    }
    return render(request, 'painel/voice/index.html', context)


@login_required(login_url='/login/')
def voice_edit(request,id):
    
    if request.method == 'GET':
            
        vox = VoiceCalls.objects.get(pk=id)
        vox_status = VoiceCalls.call_status.field.choices
        vox_days = list(range(5, 31))
        
        context = {
            'vox': vox,
            'vox_status': vox_status,
            'vox_days': vox_days,
        }
        return render(request, 'painel/voice/edit.html', context)
    
    if request.method == 'POST':
                
        call_put = VoiceCalls.objects.get(pk=id)
        status_now = call_put.call_status
        status = request.POST.get('ord_st_f')
        if request.POST.get('days'):
            call_put.days = request.POST.get('days')
        if request.POST.get('activation_date'):
            call_put.activation_date = request.POST.get('activation_date')
        else:
            call_put.activation_date = call_put.activation_date
        call_put.save()
        
        if status != status_now:
            if status == 'AT':
                voiceActivate.delay(call_put.id)
            elif status == 'DS':
                voiceDesactivate.delay(call_put.id)
            time.sleep(5)
            UpdateVoice.upStatus(call_put.id, status)
            NoteVoiceCall.addNote(id_item=call_put, note=f"Status alterado de {status_now} para {status}", id_user=request.user, type_note='P')               
            
        note_text = request.POST.get('ord_note')
        if note_text:
            NoteVoiceCall.addNote(id_item=call_put, note=note_text, id_user=request.user, type_note='P')
        
        NoteVoiceCall.addNote(id_item=call_put, note="Pedido Alterado", id_user=request.user, type_note='P')            
        messages.success(request,f'Pedido {call_put.id_item} atualizado com sucesso!')
        return redirect('voice_index')


@login_required(login_url='/login/')
def voice_import(request):
    
    if request.method == "GET":
        
        url_cdn = settings.URL_CDN
        
        context = {
            'url_cdn': url_cdn,
        }
        
        return render(request, 'painel/voice/import.html', context)
 
    if request.method == 'POST':
        try:
            voice = request.FILES.get('voice')
        except: voice = ''
        ext_name = str(voice)
        ext = ext_name[-3:]

        # Validations File
        if ext != 'csv':
            messages.error(request,'O arquivo está incorreto. Verifique por favor!')
            return render(request, 'painel/voice/import.html')     
        if voice == '':
            messages.error(request,'Campo obrigatório!')
            return render(request, 'painel/voice/import.html')

        # Validation field empty
        if voice != '':
            arquivo = voice.read().decode("utf-8")
            line_h = 0            

            for lines in arquivo.split('\n'):
                if not lines.strip():
                    continue  # pula linha vazia

                line = []
                col = lines.split(',')
                line.append(col)
                if len(col) < 3:
                    messages.error(request, 'Linha com dados insuficientes no arquivo CSV.')
                    continue
                
                f_login = line[0][0]
                f_extension = line[0][1]
                f_number = line[0][2]
                
                # Validate first line
                if line_h == 0:
                    if f_login == 'conta_sip':
                        line_h += 1
                        continue
                    else:
                        messages.error(request,'Houve um erro ao gravar a lista. Verifique se o arquivo está no formato correto')
                        return render(request, 'painel/voice/import.html')
                
                # Validate fields
                if f_login == '' or f_extension == '' or f_number == '':
                    messages.error(request,'Erro ao gravar linha')
                    continue
                
                # Validate voice
                voice_all = VoiceNumbers.objects.filter(login=f_login).exists()
                if voice_all:
                    messages.info(request,f'O SIM {line} >>> já está cadastrado no sistema <<<')
                    continue
                
                # Save Number
                add_voice = VoiceNumbers(
                    login = f_login,
                    extension = f_extension,
                    number = f_number,
                )
                add_voice.save()
                
            messages.success(request,f'Lista {line} gravada com sucesso')
            return render(request, 'painel/voice/import.html')
        else:
            messages.error(request,'Houve um ero ao gravar a lista. Verifique se o arquivo está no formato correto')
            return render(request, 'painel/voice/import.html')


def _number_list_params(request):
    src = request.POST if request.method == 'POST' else request.GET
    return {
        'number_login_f': (src.get('number_login_f') or '').strip(),
        'number_extension_f': (src.get('number_extension_f') or '').strip(),
        'number_number_f': (src.get('number_number_f') or '').strip(),
        'number_status_f': (src.get('number_status_f') or '').strip(),
    }


def _number_list_url_filter(params):
    query = {k: v for k, v in params.items() if v}
    return f'&{urlencode(query)}' if query else ''


def _number_list_redirect(params=None):
    url = reverse('mumber_list')
    if not params:
        return redirect(url)
    query = _number_list_url_filter(params)
    return redirect(f'{url}?{query[1:]}' if query else url)


@login_required(login_url='/login/')
def mumber_list(request):
    numbers_all = VoiceNumbers.objects.all().order_by('-id')
    numbers_l = numbers_all
    url_cdn = settings.URL_CDN
    params = _number_list_params(request)

    if request.method == 'POST' and 'up_status' in request.POST:
        number_id = request.POST.getlist('number_id')
        number_st = request.POST.get('number_st')
        if number_id and number_st:
            number_up_status.delay(number_id, number_st)
            messages.success(request, 'Números(s) sendo alterado(s)...')
        else:
            messages.info(request, 'Você precisa marcar alguma opção')
        return _number_list_redirect(params)

    number_login_f = params['number_login_f']
    number_extension_f = params['number_extension_f']
    number_number_f = params['number_number_f']
    number_status_f = params['number_status_f']

    if number_login_f:
        numbers_l = numbers_l.filter(login__icontains=number_login_f)
    if number_extension_f:
        numbers_l = numbers_l.filter(extension__icontains=number_extension_f)
    if number_number_f:
        numbers_l = numbers_l.filter(number__icontains=number_number_f)
    if number_status_f:
        numbers_l = numbers_l.filter(number_status=number_status_f)

    url_filter = _number_list_url_filter(params)
    num_status = VoiceNumbers.number_status.field.choices
    num_st_list = [
        (code, label, numbers_all.filter(number_status=code).count())
        for code, label in num_status
    ]

    paginator = Paginator(numbers_l, 50)
    numbers = paginator.get_page(request.GET.get('page'))

    context = {
        'numbers': numbers,
        'num_status': num_status,
        'num_st_list': num_st_list,
        'url_filter': url_filter,
        'url_cdn': url_cdn,
        'number_login_f': number_login_f,
        'number_extension_f': number_extension_f,
        'number_number_f': number_number_f,
        'number_status_f': number_status_f,
    }
    return render(request, 'painel/voice/numbers.html', context)


@login_required(login_url='/login/')
@require_POST
def up_password(request,id):

    update_password.delay(number_id=[id])   
    messages.success(request,f'Senha e QrCode redefinidos com sucesso!')

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


@login_required(login_url='/login/')
@require_POST
def atualizarDataVoz(request):
    voxs = VoiceCalls.objects.all()

    for vox in voxs:
        # if str(vox.activation_date) in ['0001-01-01', '1-01-01']:
        if str(vox.days) == '1':
            order = Orders.objects.get(pk=vox.id_item.id)
            vox.days = order.days
            # vox.activation_date = order.activation_date
            vox.save()
            logger.info(f"Voz {vox.id} atualizada com sucesso!")
    logger.info("----------------- Dados de voz atualizados com sucesso!")
    # mensagem de retorno
    messages.success(request, "Dados de voz atualizados com sucesso!")
    return redirect('voice_index')
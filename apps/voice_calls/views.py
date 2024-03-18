import os
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from apps.voice_calls.models import VoiceNumbers, VoiceCalls
from apps.voice_calls.tasks import number_up_status, voices_up_status, update_password
from apps.orders.models import Orders
from apps.orders.classes import DateFormats
import pandas as pd


@login_required(login_url='/login/')
def voice_index(request):
    global orders_l
    orders_l = None
    url_filter = ''
    voice_item_f = None
    voice_number_f = None
    voice_going_f = None
    voice_return_f = None
    voice_status_f = None
    
    url_cdn = settings.URL_CDN
    fields_df = ['id', 'id_number__number', 'id_item__client', 'id_number__id', 'id_item__item_id', 'id_number__login', 'id_number__password', 'id_number__number_qrcode', 'id_item__days', 'id_item__activation_date', 'call_status']
    
    voices_all = VoiceCalls.objects.all()    
    # Listar status dos pedidos
    vox_status = VoiceCalls.call_status.field.choices
    vox_status_dict = dict(vox_status)
    
    voices_df = pd.DataFrame((voices_all.values(*fields_df)))
    voices_df = voices_df.rename(columns={
        'id_item__item_id': 'order_id',
        'id_number__id': 'number_id',
        'id_item__client': 'client',
        'id_number__number': 'num_number',
        'id_number__login': 'num_login',
        'id_number__password': 'num_password',
        'id_number__number_qrcode': 'num_qrcode',
        'id_item__days': 'days',
        'id_item__activation_date': 'activation_date',
        })
    if voices_df:
        voices_df['activation_date'] = pd.to_datetime(voices_df['activation_date'])
        voices_df['return_date'] = voices_df['activation_date'] + pd.to_timedelta(voices_df['days'], unit='d') - pd.to_timedelta(1, unit='d')
        voices_df['call_status'] = voices_df['call_status'].map(vox_status_dict)
        voices_df['num_number'] = voices_df['num_number'].fillna(0).astype(int)
        voices_df['number_id'] = voices_df['number_id'].fillna(0).astype(int)
    
    if request.method == 'GET':
        
        if request.GET.get('voice_item_f'): voice_item_f = request.GET.get('voice_item_f')
        if request.GET.get('voice_number_f'): voice_number_f = request.GET.get('voice_number_f')    
        if request.GET.get('voice_going_f'): voice_going_f = request.GET.get('voice_going_f')       
        if request.GET.get('voice_return_f'): voice_return_f = request.GET.get('voice_return_f')    
        if request.GET.get('voice_status_f'): voice_status_f = request.GET.get('voice_status_f')

    if request.method == 'POST':
        
        if request.POST.get('voice_item_f'): voice_item_f = request.POST.get('voice_item_f')
        if request.POST.get('voice_number_f'): voice_number_f = request.POST.get('voice_number_f')    
        if request.POST.get('voice_going_f'): voice_going_f = request.POST.get('voice_going_f')
        if request.POST.get('voice_return_f'): voice_return_f = request.POST.get('voice_return_f')
        if request.POST.get('voice_status_f'): voice_status_f = request.POST.get('voice_status_f')
        
        if 'up_status' in request.POST:
            voice_id = request.POST.getlist('voice_id')
            voice_st = request.POST.get('voice_st')
            
            if voice_id and voice_st:
                voices_up_status.delay(voice_id, voice_st)
                messages.success(request,f'Pedido(s) atualizado com sucesso!')
            else:
                messages.info(request,f'Você precisa marcar alguma opção')     

    # FIlters
    
    url_filter = ''
    voices_l = voices_df
       
    if voice_item_f is not None:
        voices_l = voices_l[(voices_l['order_id'] == voice_item_f)]
        url_filter += f"&voice_item_f={voice_item_f}"
    
    if voice_number_f is not None:
        voice_number_f = int(voice_number_f)
        voices_l = voices_l[(voices_l['num_number'] == voice_number_f)]
        url_filter += f"&voice_number_f={voice_number_f}"    

    if voice_going_f is not None:
        voice_going_f = DateFormats.dateF(voice_going_f) 
        voices_l = voices_l[(voices_l['activation_date'] == voice_going_f)]
        url_filter += f"&voice_going_f={voice_going_f}"

    if voice_return_f is not None:
        voice_return_f = DateFormats.dateF(voice_return_f) 
        voices_l = voices_l[(voices_l['return_date'] == voice_return_f)]
        url_filter += f"&voice_return_f={voice_return_f}"
        
    if voice_status_f is not None:
        voice_status_f = voice_status_f 
        voices_l = voices_l[(voices_l['call_status'] == voice_status_f)]
        url_filter += f"&voice_status_f={voice_status_f}"   
        
    voices_l = voices_l.to_dict('records')

    vox_st_list = []
    for vox_s in vox_status:
        vox = voices_all.filter(call_status=vox_s[0]).count()
        vox_st_list.append((vox_s[0],vox_s[1],vox))
    
    # Paginação
    paginator = Paginator(voices_l, 50)
    page = request.GET.get('page')
    voices = paginator.get_page(page)
    
    # from rolepermissions.permissions import available_perm_status
    
    context = {
        'voices': voices,
        'vox_status': vox_status,
        'vox_st_list': vox_st_list,
        'url_cdn': url_cdn,
        'url_filter': url_filter,
    }
    return render(request, 'painel/voice/index.html', context)


@login_required(login_url='/login/')
def voice_edit(request):
    
    fields_orders = ['id','item_id','client','days','activation_date']
    orders_call = Orders.objects.filter(activation_date__gte='',id_sim__isnull=False).order_by('activation_date','item_id')   
    
    pass


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
                                
                line = []
                col = lines.split(',')
                line.append(col)
                
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


@login_required(login_url='/login/')
def mumber_list(request):
    
    global numbers_l
    numbers_l = None

    numbers_all = VoiceNumbers.objects.all().order_by('-id')
    numbers_l = numbers_all
    url_cdn = settings.URL_CDN
    
    if request.method == 'GET':
        
        number_login_f = request.GET.get('number_login_f')
        number_extension_f = request.GET.get('number_extension_f')    
        number_number_f = request.GET.get('number_number_f')
        number_status_f = request.GET.get('number_status_f')
    
    if request.method == 'POST':
        
        number_login_f = request.POST.get('number_login_f')
        number_extension_f = request.POST.get('number_extension_f')    
        number_number_f = request.POST.get('number_number_f')
        number_status_f = request.POST.get('number_status_f')
        
        print(number_login_f, number_extension_f, number_number_f, number_status_f)

        if 'up_status' in request.POST:
            number_id = request.POST.getlist('number_id')
            number_st = request.POST.get('number_st')
            
            if number_id and number_st:            
                number_up_status.delay(number_id, number_st)
                messages.success(request,f'Números(s) sendo alterado(s)...')
            else:
                messages.info(request,f'Você precisa marcar alguma opção')     
    
     # FIlters
    
    url_filter = ''

    if number_login_f:
        numbers_l = numbers_l.filter(login__icontains=number_login_f)
        url_filter += f"&number_login_f={number_login_f}"

    if number_extension_f: 
        numbers_l = numbers_l.filter(extension__icontains=number_extension_f)   
        url_filter += f"&number_extension_f={number_extension_f}"

    if number_number_f: 
        numbers_l = numbers_l.filter(number__icontains=number_number_f)
        url_filter += f"&number_number_f={number_number_f}"
    
    if number_status_f: 
        numbers_l = numbers_l.filter(number_status__icontains=number_status_f)
        url_filter += f"&number_status_f={number_status_f}"

   
    # List status
    num_status = VoiceNumbers.number_status.field.choices
    num_st_list = []
    for num_s in num_status:
        num = numbers_all.filter(number_status=num_s[0]).count()
        num_st_list.append((num_s[0],num_s[1],num))
    
    # Pagination
    paginator = Paginator(numbers_l, 50)
    page = request.GET.get('page')
    numbers = paginator.get_page(page)
    
   
    # from rolepermissions.permissions import available_perm_status
    
    context = {
        'numbers': numbers,
        'num_status': num_status,
        'num_st_list': num_st_list,
        'url_filter': url_filter,
        'url_cdn': url_cdn,
    }
    return render(request, 'painel/voice/numbers.html', context)


@login_required(login_url='/login/')
def up_password(request,id):

    update_password.delay(number_id=[id])   
    messages.success(request,f'Senha e QrCode redefinidos com sucesso!')

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
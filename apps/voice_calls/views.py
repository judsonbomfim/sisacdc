import os
from django.shortcuts import render
from django.contrib import messages
from django.core.paginator import Paginator
from apps.voice_calls.models import VoiceNumbers, VoiceCalls
from apps.voice_calls.tasks import number_up_status, voices_up_status
from apps.orders.models import Orders


def voice_index(request):
    
    voices_all = VoiceCalls.objects.all()
    voices_l = voices_all
    
    if request.method == 'GET':
        
        voice_item_f = request.GET.get('voice_item_f')
        voice_name_f = request.GET.get('voice_name_f')    
        voice_login_f = request.GET.get('voice_login_f')
        voice_status_f = request.GET.get('voice_status_f')

    if request.method == 'POST':
        
        voice_item_f = request.POST.get('voice_item_f')
        voice_name_f = request.POST.get('voice_name_f')    
        voice_login_f = request.POST.get('voice_login_f')
        voice_status_f = request.POST.get('voice_status_f')
        
        if 'up_status' in request.POST:
            voice_id = request.POST.getlist('voice_id')
            voice_st = request.POST.get('voice_st')
            
            if voice_id and voice_st:
                print('----------------------------------TAREFA')

                voices_up_status.delay(voice_id, voice_st)
                messages.success(request,f'Pedido(s) atualizado com sucesso!')
            else:
                messages.info(request,f'Você precisa marcar alguma opção')     

     # FIlters
    
    url_filter = ''

    if voice_item_f:
        voices_l = voices_l.filter(id_item__order_id__icontains=voice_item_f)
        url_filter += f"&vox_name={voice_item_f}"

    if voice_name_f: 
        voices_l = voices_l.filter(id_item__client__icontains=voice_name_f)   
        url_filter += f"&vox_order={voice_name_f}"

    if voice_login_f: 
        voices_l = voices_l.filter(id_number__login__icontains=voice_login_f)
        url_filter += f"&vox_sim={voice_login_f}"

    if voice_status_f: 
        voices_l = voices_l.filter(call_status__icontains=voice_status_f)
        url_filter += f"&vox_st={voice_status_f}"
    
    # Listar status dos pedidos
    vox_status = VoiceCalls.call_status.field.choices
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
        'url_filter': url_filter,
    }
    return render(request, 'painel/voice/index.html', context)


def mumber_list(request):

    numbers_all = VoiceNumbers.objects.all().order_by('-id')
    numbers_l = numbers_all
    
    if request.method == 'GET':
        
        voice_item_f = request.GET.get('voice_item_f')
        voice_name_f = request.GET.get('voice_name_f')    
        voice_login_f = request.GET.get('voice_login_f')
    
    if request.method == 'POST':
        
        voice_item_f = request.POST.get('voice_item_f')
        voice_name_f = request.POST.get('voice_name_f')    
        voice_login_f = request.POST.get('voice_login_f')

        if 'up_status' in request.POST:
            number_id = request.POST.getlist('number_id')
            number_st = request.POST.get('number_st')
                        
            print('----------------------------------number_id - INICIO')
            print(number_id)
            
            if number_id and number_st:
                print('----------------------------------TAREFA')
             
                number_up_status.delay(number_id, number_st)
                messages.success(request,f'Números(s) sendo alterado(s)...')
            else:
                messages.info(request,f'Você precisa marcar alguma opção')     
    
     # FIlters
    
    url_filter = ''

    if voice_item_f:
        numbers_l = numbers_l.filter(voice__icontains=voice_item_f)
        url_filter += f"&vox_name={voice_item_f}"

    if voice_name_f: 
        numbers_l = numbers_l.filter(id_item__client__icontains=voice_name_f)   
        url_filter += f"&vox_order={voice_name_f}"

    if voice_login_f: 
        numbers_l = numbers_l.filter(login__icontains=voice_login_f)
        url_filter += f"&vox_sim={voice_login_f}"

   
    # List status
    num_status = VoiceNumbers.number_status.field.choices
    num_st_list = []
    for num_s in num_status:
        num = numbers_all.filter(number_status=num_s[0]).count()
        num_st_list.append((num_s[0],num_s[1],num))

    print('num_st_list')
    print(num_st_list)
    
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
    }
    return render(request, 'painel/voice/numbers.html', context)


def voice_edit(request):
    
    fields_orders = ['id','item_id','client','days','activation_date']
    orders_call = Orders.objects.filter(activation_date__gte='',id_sim__isnull=False).order_by('activation_date','item_id')   
    
    pass


def voice_import(request):
    if request.method == "GET":
        return render(request, 'painel/voice/import.html')
 
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
                    number_status = 'DS'
                )
                add_voice.save()
                
            messages.success(request,f'Lista {line} gravada com sucesso')
            return render(request, 'painel/voice/import.html')
        else:
            messages.error(request,'Houve um ero ao gravar a lista. Verifique se o arquivo está no formato correto')
            return render(request, 'painel/voice/import.html')

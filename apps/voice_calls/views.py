import os
from django.shortcuts import render
from django.contrib import messages
from django.core.paginator import Paginator
from apps.voice_calls.models import VoiceNumbers, VoiceCalls
from apps.voice_calls.tasks import number_up_status
from apps.orders.models import Orders


def voice_index(request):
    
    global voices_l
    voices_l = ''
    
    url_cdn = str(os.getenv('URL_CDN'))
    
    voices_all = VoiceCalls.objects.all()
    voices_l = voices_all
    
    if request.method == 'GET':
        
        vox_name_f = request.GET.get('vox_name')
        vox_order_f = request.GET.get('vox_order')    
        vox_sim_f = request.GET.get('vox_sim')
        oper_f = request.GET.get('oper')
        vox_st_f = request.GET.get('vox_st')
    
    if request.method == 'POST':
        
        vox_name_f = request.POST.get('vox_name_f')
        vox_order_f = request.POST.get('vox_order_f')       
        vox_sim_f = request.POST.get('vox_sim_f')
        oper_f = request.POST.get('oper_f')
        vox_st_f = request.POST.get('vox_st_f')

        if 'up_status' in request.POST:
            vox_id = request.POST.getlist('vox_id')
            vox_s = request.POST.get('vox_staus')
            id_user = request.user.id            
                        
            print('----------------------------------vox_id')
            
            if vox_id and vox_s:
                print('----------------------------------TAREFA')
             
                voices_up_status.delay(vox_id, vox_s,id_user)
                messages.success(request,f'Pedido(s) atualizado com sucesso!')
            else:
                messages.info(request,f'Você precisa marcar alguma opção')     
    
     # FIlters
    
    url_filter = ''

    if vox_name_f:
        voices_l = voices_l.filter(client__icontains=vox_name_f)
        url_filter += f"&vox_name={vox_name_f}"

    if vox_order_f: 
        voices_l = voices_l.filter(item_id__icontains=vox_order_f)   
        url_filter += f"&vox_order={vox_order_f}"

    if vox_sim_f: 
        voices_l = voices_l.filter(id_sim__sim__icontains=vox_sim_f)
        url_filter += f"&vox_sim={vox_sim_f}"
    
    if oper_f: 
        voices_l = voices_l.filter(id_sim__operator__icontains=oper_f)
        url_filter += f"&oper={oper_f}"

    if vox_st_f: 
        voices_l = voices_l.filter(order_status__icontains=vox_st_f)
        url_filter += f"&vox_st={vox_st_f}"

    # sims = Sims.objects.all()
    # vox_status = Orders.order_status.field.choices
    # oper_list = Sims.operator.field.choices
    
    # Listar status dos pedidos
    # vox_st_list = []
    # for vox_s in vox_status:
    #     ord = voices_all.filter(order_status=vox_s[0]).count()
    #     vox_st_list.append((vox_s[0],vox_s[1],ord))
    
    # Paginação
    # paginator = Paginator(voices_l, 50)
    # page = request.GET.get('page')
    # orders = paginator.get_page(page)
    
    # from rolepermissions.permissions import available_perm_status
    
    context = {
        # 'url_cdn': url_cdn,
        # 'voices_l': voices_l,
        # 'orders': orders,
        # 'sims': sims,
        # 'vox_st_list': vox_st_list,
        # 'oper_list': oper_list,
        # 'url_filter': url_filter,
    }
    return render(request, 'painel/voice/index.html', context)

def mumber_list(request):

    voices_l = ''
    
    url_cdn = str(os.getenv('URL_CDN'))
    
    # voices_all = VoiceCalls.objects.all().order_by('-id')
    numbers_all = VoiceNumbers.objects.all().order_by('-id')
    numbers_l = numbers_all
    
    if request.method == 'GET':
        
        login_f = request.GET.get('login_f')
        extension_f = request.GET.get('extension_f')    
        number_f = request.GET.get('number_f')
        number_status_f = request.GET.get('number_status_f')
    
    if request.method == 'POST':
        
        login_f = request.POST.get('login_f')
        extension_f = request.POST.get('extension_f')       
        number_f = request.POST.get('number_f')
        number_status_f = request.POST.get('number_status_f')

        if 'up_status' in request.POST:
            number_id = request.POST.getlist('number_id')
            number_st = request.POST.get('number_st')
            id_user = request.user.id         
                        
            print('----------------------------------number_id - INICIO')
            print(number_id)
            
            if number_id and number_st:
                print('----------------------------------TAREFA')
             
                number_up_status.delay(number_id, number_st, id_user)
                messages.success(request,f'Números(s) sendo alterado(s)...')
            else:
                messages.info(request,f'Você precisa marcar alguma opção')     
    
     # FIlters
    
    url_filter = ''

    if login_f:
        numbers_l = numbers_l.filter(login__icontains=login_f)
        url_filter += f"&vox_name={login_f}"

    if extension_f: 
        numbers_l = numbers_l.filter(extension__icontains=extension_f)   
        url_filter += f"&vox_order={extension_f}"

    if number_f: 
        numbers_l = numbers_l.filter(number__icontains=number_f)
        url_filter += f"&vox_sim={number_f}"
    
    if number_status_f: 
        numbers_l = numbers_l.filter(number_status__icontains=number_status_f)
        url_filter += f"&oper={number_status_f}"

    # sims = Sims.objects.all()
    number_status = VoiceNumbers.number_status.field.choices
    
    print(number_status)
    # oper_list = Sims.operator.field.choices

    # Listar status dos pedidos
    # vox_st_list = []
    # for vox_s in vox_status:
    #     ord = voices_all.filter(order_status=vox_s[0]).count()
    #     vox_st_list.append((vox_s[0],vox_s[1],ord))

    # Pagination
    paginator = Paginator(numbers_l, 50)
    page = request.GET.get('page')
    numbers = paginator.get_page(page)
    
    # from rolepermissions.permissions import available_perm_status
    
    context = {
        # 'url_cdn': url_cdn,
        # 'numbers_l': numbers_l,
        # 'orders': orders,
        'numbers': numbers,
        'number_status': number_status,
        # 'oper_list': oper_list,
        # 'url_filter': url_filter,
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

from django.contrib.auth.decorators import login_required
from rolepermissions.decorators import has_permission_decorator
from django.shortcuts import render
from django.http import HttpResponse
from django.urls import reverse
import csv
import os
from datetime import date
from django.core.paginator import Paginator
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from apps.sims.models import Sims
from apps.orders.models import Orders
from apps.orders.views import ApiStore, StatusSis

@login_required(login_url='/login/')
def sims_list(request):
    global sims_l
    sims_l = ''
    
    sims_all = Sims.objects.all().order_by('-id')
    sims_l = sims_all
    
    if request.method == 'GET':
        
        sim_f = request.GET.get('sim')
        sim_type_f = request.GET.get('sim_type')    
        sim_status_f = request.GET.get('sim_status')
        sim_oper_f = request.GET.get('sim_oper')
    
    if request.method == 'POST':
        
        sim_f = request.POST.get('sim_f')
        sim_type_f = request.POST.get('sim_type_f')       
        sim_status_f = request.POST.get('sim_status_f')
        sim_oper_f = request.POST.get('sim_oper_f')
            
        if 'up_status' in request.POST:
                sim_id = request.POST.getlist('sim_id')
                sim_st = request.POST.get('sim_st')
                if sim_id and sim_st:
                    for o_id in sim_id:
                        sim = Sims.objects.get(pk=o_id)
                        sim.sim_status = sim_st
                        sim.save()
                        
                    messages.success(request,f'SIM(s) atualizado(s) com sucesso!')
                else:
                    messages.info(request,f'Você precisa marcar alguma opção')
    
    # FIlters
    
    url_filter = ''
    
    if sim_f:
        sims_l = sims_l.filter(sim__icontains=sim_f)
        url_filter += f"&sim={sim_f}"

    if sim_type_f: 
        sims_l = sims_l.filter(type_sim__icontains=sim_type_f)        
        url_filter += f"&sim_type={sim_type_f}"
    
    if sim_status_f: 
        sims_l = sims_l.filter(sim_status__icontains=sim_status_f)
        url_filter += f"&sim_status={sim_status_f}"
    
    if sim_oper_f: 
        sims_l = sims_l.filter(operator__icontains=sim_oper_f)
        url_filter += f"&sim_oper={sim_oper_f}"
        
    
    sims_types = Sims.type_sim.field.choices
    sims_status = Sims.sim_status.field.choices
    sims_oper = Sims.operator.field.choices
    
    paginator = Paginator(sims_l, 50)
    page = request.GET.get('page')
    sims = paginator.get_page(page)
    
    # Verificar estoque de operadoras
    sim_tm = sims_all.filter(sim_status='DS',operator='TM', type_sim='sim').count()
    esim_tm = sims_all.filter(sim_status='DS',operator='TM', type_sim='esim').count()
    sim_cm = sims_all.filter(sim_status='DS',operator='CM', type_sim='sim').count()
    esim_cm = sims_all.filter(sim_status='DS',operator='CM', type_sim='esim').count()
    sim_tc = sims_all.filter(sim_status='DS',operator='TC', type_sim='sim').count()
    esim_tc = sims_all.filter(sim_status='DS',operator='TC', type_sim='esim').count()
    
    url = reverse('sims_index')
    
    context= {
        'url': url,
        'sims': sims,
        'sims_types': sims_types,
        'sims_status': sims_status,
        'sims_oper': sims_oper,
        'sim_tm': sim_tm,
        'esim_tm': esim_tm,
        'sim_cm': sim_cm,
        'esim_cm': esim_cm,
        'sim_tc': sim_tc,
        'esim_tc': esim_tc,
        'url_filter': url_filter,
    }
       
    return render(request, 'painel/sims/index.html', context)

@login_required(login_url='/login/')
def sims_add_sim(request):
    if request.method == "GET":
        
        return render(request, 'painel/sims/add-sim.html')
        
    if request.method == 'POST':
        
        type_sim = request.POST.get('type_sim')
        operator = request.POST.get('operator')
        sim = request.FILES.get('sim')
        ext_nome = str(sim)
        ext = ext_nome[-3:]
        
        # Validations
        if ext != 'csv':
            messages.error(request,'O arquivo está incorreto. Verifique por favor!')
            return render(request, 'painel/sims/add-sim.html')     
        if type_sim == '' or operator == '' or sim == '':
            messages.error(request,'Preencha todos os campos')
            return render(request, 'painel/sims/add-sim.html')
        
        try:
            arquivo = sim.read().decode("utf-8")
            linha_h = 0
            for linha in arquivo.split():
                # Validate first line
                if linha_h == 0:
                    if linha == 'upload_sims':
                        linha_h += 1
                        continue
                    else:
                        messages.error(request,'Houve um erro ao gravar a lista. Verifique se o arquivo está no formato correto')
                        return render(request, 'painel/sims/add-sim.html')
                
                sims_all = Sims.objects.all().filter(sim=linha).filter(type_sim='sim')
                if sims_all:
                    messages.info(request,f'O SIM {linha} já está cadastrado no sistema')
                    continue
                  
                # Save SIMs
                add_sim = Sims(
                    sim = linha,
                    type_sim = type_sim,
                    operator = operator
                )
                add_sim.save()
                
            messages.success(request,'Lista gravada com sucesso')
            return render(request, 'painel/sims/add-sim.html')
        except:
            messages.error(request,'Houve um ero ao gravar a lista. Verifique se o arquivo está no formato correto')
            return render(request, 'painel/sims/add-sim.html')

@login_required(login_url='/login/')
def sims_add_esim(request):
    if request.method == "GET":
        
        return render(request, 'painel/sims/add-esim.html')
        
    if request.method == 'POST':
                
        type_sim = request.POST.get('type_sim')
        operator = request.POST.get('operator')
        esims = request.FILES.getlist('esim')
 
        if type_sim == '' or operator == '' or esims == '':
            messages.error(request,'Preencha todos os campos')
            return render(request, 'painel/sims/add-esim.html')
                           
        try:
            for sim_img in esims:
                sim_i = sim_img.name.split('.')
                # Save image
                fs = FileSystemStorage()
                file = fs.save(sim_img.name, sim_img)
                fileurl = fs.url(file)
                
                sims_all = Sims.objects.all().filter(sim=sim_i[0]).filter(type_sim='esim')
                if sims_all:
                    messages.info(request,f'O SIM {sim_i[0]} já está cadastrado no sistema')
                    continue
                # Save SIMs
                add_sim = Sims(
                    sim = sim_i[0],
                    link = fileurl,
                    type_sim = type_sim,
                    operator = operator
                )
                add_sim.save()

            messages.success(request,'Lista gravada com sucesso')
            return render(request, 'painel/sims/add-esim.html')
        except:
            messages.error(request,'Houve um erro ao gravar os eSIMs')
            return render(request, 'painel/sims/add-esim.html')

@login_required(login_url='/login/')
def sims_ord(request):
    if request.method == "GET":
        return render(request, 'painel/sims/sim-order.html')
    
    if request.method == 'POST':
        orders = Orders.objects.filter(order_status='AS')
        
        global n_item_total
        n_item_total = 0
        global msg_ord
        msg_info = []
        global msg_error
        msg_error = []
        
        for ord in orders:
            
            id_id_i = ord.id
            order_id_i = ord.order_id
            product_i = ord.product
            countries_i = ord.countries
            type_sim_i = ord.type_sim
            update_store = {}
            
            # if product_i == 'chip-internacional-eua':
            #     operator_i = 'TM'
            # else: operator_i = 'CM'
     

            # Escolher operadora
            # if product_i == 'chip-internacional-europa' and countries_i == False and type_sim_i == 'esim':
            if product_i == 'chip-internacional-europa' and countries_i == False:
                operator_i = 'TC'
            elif product_i == 'chip-internacional-eua':
                operator_i = 'TM'
            else: operator_i = 'CM'            
            
            # First SIM
            sim_ds = Sims.objects.all().order_by('id').filter(operator=operator_i, type_sim=type_sim_i, sim_status='DS').first()
            if sim_ds:
                pass
            else:                
                msg_error.append(f'Não há estoque de {operator_i} - {type_sim_i} no sistema')
                continue
            
            # update order
            # Save SIMs
            if sim_ds.type_sim == 'esim':
                status_ord = 'EE'
            else: status_ord = 'ES'
            
            order_put = Orders.objects.get(pk=id_id_i)
            order_put.id_sim_id = sim_ds.id            
            order_put.order_status = status_ord
            order_put.save()
            
            # update sim
            sim_put = Sims.objects.get(pk=sim_ds.id)
            sim_put.sim_status = 'AT'
            sim_put.save()           
            
            status_sis_site = StatusSis.st_sis_site()
                    
            if status_ord in status_sis_site:
                update_store = {
                    'status': status_sis_site[status_ord]
                }
            # Enviar eSIM para site
            if sim_put.type_sim == 'esim':
                url_painel = str(os.getenv('URL_PAINEL'))
                esims_order = Orders.objects.filter(order_id=order_id_i).filter(type_sim='esim')
                esims_list = ''
                for esims_o in esims_order:
                    try:
                        link_sim = esims_o.id_sim.link              
                        esims_list = esims_list + f"<img src='{url_painel}{link_sim}' style='width: 300px; margin:40px;'>"
                        update_store = {
                            "meta_data":[
                                {
                                    "key": "campo_esims",
                                    "value": esims_list
                                },
                            ]
                        }
                    except:
                        update_store = {
                            "meta_data":[
                                {
                                    "key": "campo_esims",
                                    "value": ''
                                },
                            ]
                        }
                
            apiStore = ApiStore.conectApiStore()                    
            apiStore.put(f'orders/{order_id_i}', update_store).json()
            
            msg_info.append(f'Pedido {order_id_i} atualizados com sucesso')
            
            n_item_total += 1 
    if n_item_total == 0:
        messages.info(request,'Não há pedido(s) para atualizar!')
    else:
        for msg_e in msg_error:
            messages.error(request,msg_e)
        for msg_o in msg_info:
            messages.info(request,msg_o)
        messages.success(request,'Todos os pedido(s) atualizados com sucesso')   
        
    return render(request, 'painel/sims/sim-order.html')

@login_required(login_url='/login/')
def exportSIMs(request):
    
    sims_all = Sims.objects.all().order_by('id')
    data = [
        ['ID', 'SIM', 'Tipo', 'Operadora', 'Status']
    ]
    for sim in sims_all:
        data.append([sim.id,sim.sim,sim.type_sim,sim.operator,sim.sim_status])
    
    data_atual = date.today()
    # Crie um objeto CSVWriter para escrever os dados no formato CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="Estoque SIMs-{data_atual}.csv"'
    writer = csv.writer(response)

    # Escreva os dados no objeto CSVWriter
    for row in data:
        writer.writerow(row)

    return response

login_required(login_url='/login/')
def delSIMs(request):
    orders = Orders.objects.all()
    
    sims_cc = Sims.objects.filter(sim_status='CC')
    sims_tc = Sims.objects.filter(sim_status='TC')
    
    for sim in sims_cc:
        if orders.filter(id_sim=sim.id):
            continue
        sim.delete()
    
    for sim in sims_tc:
        if orders.filter(id_sim=sim.id):
            continue
        sim.delete()
    
    return HttpResponse('SIMs deletados com sucesso')

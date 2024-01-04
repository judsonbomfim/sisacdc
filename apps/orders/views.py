from django.contrib.auth.models import User
from rolepermissions.decorators import has_permission_decorator
import os
import csv
from django.http import HttpResponse
from datetime import date, datetime, timedelta
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils.text import slugify
from apps.orders.models import Orders, Notes
from apps.sims.models import Sims
from apps.send_email.classes import SendEmail
from .classes import ApiStore, StatusSis
import pandas as pd
import json

#Date today
today = datetime.now()

# Date - 2023-05-16T18:40:27
def dateHour(dh):
    date = dh[0:10]
    hour = dh[11:19]
    date_hour = f'{date} {hour}'
    return date_hour
# Date - 17/06/2023
def dateF(d):
    dia = d[0:2]
    mes = d[3:5]
    ano = d[6:10]
    dataForm = f'{ano}-{mes}-{dia}'
    return dataForm
# Date - 2023-05-17 00:56:18+00:00 > 00/00/00
def dateDMA(dma):
    ano = dma[2:4]
    mes = dma[5:7]
    dia = dma[8:10]
    data_dma = f'{dia}/{mes}/{ano}'
    return data_dma

def updateEsimStore(order_id):    
    url_painel = str(os.getenv('URL_PAINEL'))
    esims_order = Orders.objects.filter(order_id=order_id).filter(id_sim__link__isnull=False)
    esims_list = ''
    update_store = {"meta_data":[{"key": "campo_esims","value": ''}]}
    if esims_order:
        for esims_o in esims_order:
            link_sim = esims_o.id_sim.link              
            esims_list = esims_list + f"<img src='{url_painel}{link_sim}' style='width: 300px; margin:40px;'>"
            update_store = {
                "meta_data": [
                    {
                        "key": "campo_esims",
                        "value": esims_list
                    }
                ]
            }
    else:
        pass
    # Conect Store
    apiStore = ApiStore.conectApiStore()
    apiStore.put(f'orders/{order_id}', update_store).json() 

# Order list
@login_required(login_url='/login/')
@has_permission_decorator('view_orders')
def orders_list(request):
    global orders_l
    orders_l = ''
    
    orders_all = Orders.objects.all().order_by('-id')
    orders_l = orders_all
    
    if request.method == 'GET':
        
        ord_name_f = request.GET.get('ord_name')
        ord_order_f = request.GET.get('ord_order')    
        ord_sim_f = request.GET.get('ord_sim')
        oper_f = request.GET.get('oper')
        ord_st_f = request.GET.get('ord_st')
    
    if request.method == 'POST':
        
        ord_name_f = request.POST.get('ord_name_f')
        ord_order_f = request.POST.get('ord_order_f')       
        ord_sim_f = request.POST.get('ord_sim_f')
        oper_f = request.POST.get('oper_f')
        ord_st_f = request.POST.get('ord_st_f')

        if 'up_status' in request.POST:
            ord_id = request.POST.getlist('ord_id')
            ord_s = request.POST.get('ord_staus')
            if ord_id and ord_s:
                for o_id in ord_id:
                    
                    order = Orders.objects.get(pk=o_id)
                    order.order_status = ord_s
                    order.save()
                    
                    order_id = order.order_id
                    order_st = order.order_status
                    order_plan = order.get_product_display()
                    try: type_sim = order.id_sim.type_sim
                    except: type_sim = 'esim'
                    apiStore = ApiStore.conectApiStore()
                    
                    if ord_s == 'CC' or ord_s == 'DS':
                        if order.id_sim:
                            # Update SIM
                            sim_put = Sims.objects.get(pk=order.id_sim.id)
                            if order.id_sim.type_sim == 'esim':
                                sim_put.sim_status = 'TC'
                                esim_v = True
                            else:
                                sim_put.sim_status = 'DS'
                            sim_put.sim_status = 'TC'
                            sim_put.save()
                                
                            # Delete SIM in Order
                            order_put = Orders.objects.get(pk=order.id)
                            order_put.id_sim_id = ''
                            order_put.save()
                            
                            # Deletar eSIM para site                            
                            if esim_v == True:    
                                updateEsimStore(order_id)
                        
                    # Save Notes
                    def addNote(t_note):
                        add_sim = Notes( 
                            id_item = Orders.objects.get(pk=order.id),
                            id_user = User.objects.get(pk=request.user.id),
                            note = t_note,
                            type_note = 'S',
                        )
                        add_sim.save()
                    
                    ord_status = Orders.order_status.field.choices
                    for st in ord_status:
                        if order_st == st[0] :    
                            addNote(f'Alterado de {st[1]} para {order.get_order_status_display()}')
                    
                    # Alterar status
                    # Status sis : Status Loja
                    status_sis_site = StatusSis.st_sis_site()
                    
                    if ord_s in status_sis_site:
                        update_store = {
                            'status': status_sis_site[ord_s]
                        }
                        apiStore.put(f'orders/{order.order_id}', update_store).json()
                    
                    # Enviar email
                    if ord_s == 'CN' and (type_sim == 'sim' or order_plan == 'USA'):
                        SendEmail.mailAction(id=order.id)
                        
                        addNote(f'E-mail enviado com sucesso!')
                        messages.success(request,'E-mail enviado com sucesso!')
                    
                messages.success(request,f'Pedido(s) atualizado com sucesso!')
            else:
                messages.info(request,f'Você precisa marcar alguma opção')        
    
     # FIlters
    
    url_filter = ''

    if ord_name_f:
        orders_l = orders_l.filter(client__icontains=ord_name_f)
        url_filter += f"&ord_name={ord_name_f}"

    if ord_order_f: 
        orders_l = orders_l.filter(item_id__icontains=ord_order_f)   
        url_filter += f"&ord_order={ord_order_f}"

    if ord_sim_f: 
        orders_l = orders_l.filter(id_sim__sim__icontains=ord_sim_f)
        url_filter += f"&ord_sim={ord_sim_f}"
    
    if oper_f: 
        orders_l = orders_l.filter(id_sim__operator__icontains=oper_f)
        url_filter += f"&oper={oper_f}"

    if ord_st_f: 
        orders_l = orders_l.filter(order_status__icontains=ord_st_f)
        url_filter += f"&ord_st={ord_st_f}"

    sims = Sims.objects.all()
    ord_status = Orders.order_status.field.choices
    oper_list = Sims.operator.field.choices
    
    # Listar status dos pedidos
    ord_st_list = []
    for ord_s in ord_status:
        ord = orders_all.filter(order_status=ord_s[0]).count()
        ord_st_list.append((ord_s[0],ord_s[1],ord))
    
    # Paginação
    paginator = Paginator(orders_l, 50)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    context = {
        'orders_l': orders_l,
        'orders': orders,
        'sims': sims,
        'ord_st_list': ord_st_list,
        'oper_list': oper_list,
        'url_filter': url_filter,
    }
    return render(request, 'painel/orders/index.html', context)
    
# Update orders
@login_required(login_url='/login/')
@has_permission_decorator('import_orders')
def ord_import(request):
    if request.method == 'GET':

        return render(request, 'painel/orders/import.html')    
       
    if request.method == 'POST':
        apiStore = ApiStore.conectApiStore()
        
        global n_item_total
        n_item_total = 0
        global msg_info
        msg_info = []
        global msg_error
        msg_error = []
        
        # Definir números de páginas
        per_page = 100
        date_now = datetime.now()
        start_date = date_now - timedelta(days=7)
        end_date = date_now
        order_p = apiStore.get('orders', params={'after': start_date, 'before': end_date, 'status': 'processing', 'per_page': per_page})        
        
        total_pages = int(order_p.headers['X-WP-TotalPages'])
        n_page = 1
        
        # orders_all = Orders.objects.all()
        
        while n_page <= total_pages:
            # Pedidos com status 'processing'
            ord = apiStore.get('orders', params={'order': 'asc', 'status': 'processing', 'per_page': per_page, 'page': n_page}).json()                                   

            # Listar pedidos         
            for order in ord:
                n_item = 1
                id_ord = order["id"]
                
                # Verificar pedido repetido

                id_sis = Orders.objects.filter(order_id=id_ord)
                if id_sis:
                    continue
                else: pass
                
                # Listar itens do pedido
                for item in order['line_items']:
                                        
                    # Especificar produtos a serem listados
                    prod_sel = [50760, 8873, 8791, 8761]
                    if item['product_id'] not in prod_sel:
                        continue
                                 
                    qtd = item['quantity']
                    q_i = 1 
                    
                    while q_i <= qtd:
                        order_id_i = order['id']
                        item_id_i = f'{order_id_i}-{n_item}'
                        client_i = f'{order["billing"]["first_name"]} {order["billing"]["last_name"]}'
                        email_i = order['billing']['email']
                        if "Global" in item['name']:
                            product_i = 'chip-internacional-global'
                        else:
                            product_i = slugify(item['name'])
                        
                        qty_i = 1
                        if order['coupon_lines']:
                            coupon_i = order['coupon_lines'][0]['code']
                        else: coupon_i = '-'
                        # Definir valor padrão para variáveis
                        ord_chip_nun_i = '-'
                        countries_i = False
                        cell_mod_i = False
                        # Percorrer itens do pedido
                        for i in item['meta_data']:
                            if i['key'] == 'pa_tipo-de-sim': type_sim_i = i['value']
                            if i['key'] == 'pa_condicao-do-chip': condition_i = i['value']
                            if i['key'] == 'pa_dados-diarios': data_day_i = i['value']
                            if i['key'] == 'pa_dias': days_i = i['value']
                            if i['key'] == 'pa_plano-de-voz': 
                                if i['value'] == 'sem-ligacoes': calls_i = False
                                else: calls_i = True
                            if 'Visitará' in i['key']:
                                if i['display_value'] == 'Sim': countries_i = True 
                                else: countries_i = False
                            if i['key'] == 'Data de Ativação': activation_date_i = i['value']
                            if i['key'] == 'Modelo e marca de celular': cell_mod_i = i['value']
                            if i['key'] == 'Número de pedido ou do chip': ord_chip_nun_i = i['value']
                        shipping_i = order['shipping_lines'][0]['method_title']
                        order_date_i = dateHour(order['date_created'])
                        # notes_i = 0
                        
                        # Definir status do pedido
                        # 'RT', 'Retirada'
                        # 'MB', 'Motoboy'
                        # 'RS', 'Reuso'
                        # 'AS', 'Atribuir SIM'
                        if 'RETIRADA' in shipping_i:
                            shipping_i = 'Retirada SP'
                            order_status_i = 'RT'
                        elif 'Entrega na Agência' in shipping_i:
                            shipping_i = 'Entr. Agência'
                            order_status_i = 'AG'
                        elif 'Motoboy' in shipping_i:
                            order_status_i = 'MB'
                        elif condition_i == 'reuso-sim':
                            order_status_i = 'RS'
                        else:
                            order_status_i = 'AS'                    
                        
                        # Definir variáveis para salvar no banco de dados                            
                        order_add = Orders(                    
                            order_id = order_id_i,
                            item_id = item_id_i,
                            client = client_i,
                            email = email_i,
                            product = product_i,
                            data_day = data_day_i,
                            qty = qty_i,
                            coupon = coupon_i,
                            condition = condition_i,
                            days = days_i,
                            calls = calls_i,
                            countries = countries_i,
                            cell_mod = cell_mod_i,
                            ord_chip_nun = ord_chip_nun_i,
                            shipping = shipping_i,
                            order_date = order_date_i,
                            activation_date = activation_date_i,
                            order_status = order_status_i,
                            type_sim = type_sim_i,
                            # notes = notes_i
                        )
                        
                        # Salvar itens no banco de dados
                        register = order_add.save()
                        try:
                            register
                        except:
                            msg_error.append(f'Pedido {order_id_i} deu um erro ao importar')
                            
                        # Save Notes
                        add_sim = Notes( 
                            id_item = Orders.objects.get(pk=order_add.id),
                            id_user = User.objects.get(pk=request.user.id),
                            note = f'Pedido importado para o sistema',
                            type_note = 'S',
                        )
                        add_sim.save()                       
                        
                        # Alterar status
                        # Status sis : Status Loja
                        status_def_sis = StatusSis.st_sis_site()
                        if order_status_i in status_def_sis:
                            status_ped = {
                                'status': status_def_sis[order_status_i]
                            }
                            try:                                  
                                apiStore.put(f'orders/{order_id_i}', status_ped).json()
                            except:
                                msg_error.append(f'{order_id_i} - Falha ao atualizar status na loja!')
                        
                        # Definir variáveis
                        q_i += 1 
                        n_item += 1
                        n_item_total += 1
                        
                        msg_info.append(f'Pedido {order_id_i} atualizados com sucesso')
                        
            n_page += 1            
                            
    # Mensagem de sucesso
    if n_item_total == 0:
        messages.info(request,'Não há pedido(s) para atualizar!')
    else:
        for msg_e in msg_error:
            messages.error(request,msg_e)
        for msg_o in msg_info:
            messages.info(request,msg_o)
        messages.success(request,'Todos os pedido(s) atualizados com sucesso')
    return render(request, 'painel/orders/import.html')

# Order Edit
@login_required(login_url='/login/')
@has_permission_decorator('edit_orders')
def ord_edit(request,id):
    if request.method == 'GET':
            
        order = Orders.objects.get(pk=id)
        ord_status = Orders.order_status.field.choices
        ord_product = Orders.product.field.choices
        ord_data_day = Orders.data_day.field.choices
        
        context = {
            'order': order,
            'ord_status': ord_status,
            'ord_product': ord_product,
            'ord_data_day': ord_data_day,
            'days': range(1, 31),
        }
        return render(request, 'painel/orders/edit.html', context)
        
    if request.method == 'POST':
        
        global msg_info
        msg_info = []
        global msg_error
        msg_error = []
        global id_sim
        id_sim = ''
        global ord_st
        ord_st = ''
        global update_store
        update_store = {}
        
        order = Orders.objects.get(pk=id)
        order_id = order.order_id
        try: order_sim = order.id_sim.sim
        except: order_sim = ''
        days = request.POST.get('days')
        product = request.POST.get('product')
        data_day = request.POST.get('data_day')
        type_sim = request.POST.get('type_sim')
        operator = request.POST.get('operator')
        sim = request.POST.get('sim')
        activation_date = request.POST.get('activation_date')
        cell_imei = request.POST.get('cell_imei')
        cell_eid = request.POST.get('cell_eid')
        tracking = request.POST.get('tracking')
        ord_st = request.POST.get('ord_st_f')
        ord_note = request.POST.get('ord_note')
        up_oper = request.POST.get('upOper')
        esim_v = None
        
        # Update SIM in Order and update SIM
        def updateSIM():
            # Update SIM
            sim_put = Sims.objects.get(pk=order.id_sim.id)            
            sim_put.sim_status = 'TC'
            sim_put.save()
            # Delete SIM in Order
            order_put = Orders.objects.get(pk=order.id)
            order_put.id_sim_id = ''
            order_put.save()
        
        # Insert SIM in Order
        def insertSIM(ord_st=None):
            sim_up = Sims.objects.filter(sim_status='DS', type_sim=type_sim, operator=operator).first()
            if sim_up:
                sim_put = Sims.objects.get(pk=sim_up.id)
                if order.id_sim:
                    # Update SIM
                    updateSIM()
                sim_put.sim_status = 'AT'
                sim_put.save()
                
                if type_sim == 'esim': 
                    ord_st = 'EE'
                else: ord_st = ord_st
                
                order_put = Orders.objects.get(pk=order.id)
                order_put.id_sim_id = sim_put.id
                order_put.order_status = ord_st
                order_put.save()
            else:       
                msg_error.append(f'Não há estoque de {operator} - {type_sim} no sistema')
            
        # Se SIM preenchico
        if sim:
            # Verificar se Operadora e Tipo de SIM estão marcados
            if type_sim =='esim':
                msg_error.append(f'Não é possível adicionar um eSIM desta forma')
            elif operator != None and type_sim != None:
                if order.id_sim:
                    # Alterar status no sistema e no site
                    updateSIM()
                
                sims_all = Sims.objects.all().filter(sim=sim)
                if sims_all:
                    if order.condition == 'reuso-sim':
                        # Update order
                        sim_id = sims_all[0].id
                        sims_put = Sims.objects.get(pk=sim_id)
                        sims_put.sim_status = 'AT'
                        sims_put.save()
                        order_put = Orders.objects.get(pk=order.id)
                        order_put.id_sim_id = sim_id
                        order_put.save()
                        up_plan = True # verificação para nota
                    else:
                        messages.info(request,f'O SIM {sim} já está cadastrado no sistema')
                else:
                    # Save SIMs - Insert Stock
                    add_sim = Sims( 
                        sim = sim,
                        type_sim = type_sim,
                        operator = operator,
                        sim_status = 'AT',
                    )
                    add_sim.save()
                
                    # Update order
                    order_put = Orders.objects.get(pk=order.id)
                    order_put.id_sim_id = add_sim.id
                    order_put.save()
                    up_plan = True # verificação para nota
            else:
                msg_error.append(f'Você precisa selecionar o tipo de SIM e a Operadora')
        else:
            # Troca de SIM
            if order.id_sim:
                if order.id_sim.operator != operator or order.id_sim.type_sim != type_sim or up_oper != None:
                    updateSIM()
                    insertSIM(ord_st)
                    up_plan = True # verificação para nota
                    
                    # Update SIM
                    esim_v = True             
            else:
                if operator != None and type_sim != None:
                    insertSIM(ord_st)
                    up_plan = True # verificação para nota

                    
        # Liberar SIMs
        if ord_st == 'CC':
            
            if order.id_sim:
                updateSIM()
            
        # Update Order
        if activation_date == '':
            activation_date = order.activation_date
                
        order_put = Orders.objects.get(pk=order.id)
        order_put.days = days
        order_put.product = product
        order_put.data_day = data_day
        order_put.activation_date = activation_date
        order_put.cell_imei = cell_imei
        order_put.cell_eid = cell_eid
        order_put.tracking = tracking
        order_put.order_status = ord_st
        order_put.save()
        
        # Notes
        def addNote(t_note):
            add_sim = Notes( 
                id_item = Orders.objects.get(pk=order.id),
                id_user = User.objects.get(pk=request.user.id),
                note = t_note,
                type_note = 'S',
            )
            add_sim.save()
        # Save Notes
        if ord_note:
            addNote(ord_note)
        # Date Notes
        if activation_date != order.activation_date:
            addNote(f'Alteração de {dateDMA(str(order.activation_date))} para {dateDMA(str(activation_date))}')
        # SIM Notes
        if sim:
            addNote(f'Alteração de {order_sim} para {sim}')
        # Plan Notes
        try:
            if up_plan:
                addNote(f'Plano alterado')
        except: pass
        
        # Conect Store
        apiStore = ApiStore.conectApiStore() 
            
        # Status Notes
        if ord_st != order.order_status:
            # Alterar status
            # Status sis : Status Loja
            status_sis_site = StatusSis.st_sis_site()
            if ord_st in status_sis_site:            
                
                update_store = {
                    'status': status_sis_site[ord_st]
                }
            apiStore.put(f'orders/{order.order_id}', update_store).json()
            
            # Salvar notas    
            ord_status = Orders.order_status.field.choices
            for st in ord_status:
                if ord_st == st[0] :
                    addNote(f'Alterado de {order.get_order_status_display()} para {st[1]}')
            
            # Enviar email
            if ord_st == 'CN' and type_sim == 'sim':
                id_user = User.objects.get(pk=request.user.id)
                SendEmail.mailAction(id=order.id,id_user=id_user)
                
                addNote(f'E-mail enviado com sucesso!')
                messages.success(request,'E-mail enviado com sucesso!')
        
        if type_sim == 'esim' or esim_v == True:
            # Enviar eSIM para site
            updateEsimStore(order_id) 
        
        for msg_e in msg_error:
            messages.error(request,msg_e)
        for msg_o in msg_info:
            messages.info(request,msg_o)
        messages.success(request,f'Pedido {order.order_id} atualizado com sucesso!')
        return redirect('orders_list')

@login_required(login_url='/login/')
@has_permission_decorator('export_orders')
def ord_export_op(request):
    
    sims_op = Sims.operator.field.choices
    context= {
        'sims_op': sims_op,
    }  
    
    if request.method == 'POST':
        
        ord_op_f = request.POST.get('ord_op_f')
        
        orders_all = Orders.objects.all().order_by('id').filter(order_status='AA')
        
        if ord_op_f != 'op_all':
            orders_all = orders_all.filter(id_sim_id__operator__icontains=ord_op_f)
            
        # Crie uma lista com os dados que você deseja exportar para o CSV
        data = [
            ['Data Compra', 'Pedido', '(e)SIM', 'EID', 'IMEI','Plano', 'Dias', 'Data Aivação', 'Operadora', 'Voz', 'Países']
        ]
        
        ord_prod_list = {
            'chip-internacional-eua': 'T-Mobile',
            'chip-internacional-eua-e-canada': 'USA E CANADA',
            'chip-internacional-europa': 'EUROPA',
            'chip-internacional-global': 'GLOBAL PREMIUM',
        }
        
        for ord in orders_all:
            ord_date = dateDMA(str(ord.order_date))
            if ord.data_day != 'ilimitado': 
                ord_data = ord.get_data_day_display()
            else: ord_data = ''
            ord_product = f'{ord_prod_list[ord.product]} {ord_data}'
            ord_date_act = dateDMA(str(ord.activation_date))
            if ord.id_sim:
                ord_op = ord.id_sim.get_operator_display()
                ord_sim = ord.id_sim.sim
            else:
                ord_op = '-'
                ord_sim = '-'
            if ord.calls == True:
                ord_calls = 'SIM'
            else: ord_calls = ''
            if ord.countries == True:
                ord_countries = 'SIM'
            else: ord_countries = ''
            data.append([ord_date,ord.item_id,ord_sim,ord.cell_eid,ord.cell_imei,ord_product,ord.days,ord_date_act,ord_op,ord_calls,ord_countries])

        data_atual = date.today()
        
        # Crie um objeto CSVWriter para escrever os dados no formato CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="Ativacoes-{data_atual}-{ord_op_f}.csv"'
        writer = csv.writer(response)

        # Escreva os dados no objeto CSVWriter
        for row in data:
            writer.writerow(row)

        messages.success(request, 'Arquivo CSV baixado com sucesso!')
        return response 
    
    return render(request, 'painel/orders/export_op.html', context)

def send_esims(request):
    if request.method == 'GET':
        return render(request, 'painel/orders/send_esim.html')    

def orders_activations(request):
    global orders_l
    orders_l = None
    url_filter = ''
    activGoing_f = None
    activGoing_1 = None
    activGoing_2 = None
    activReturn_f = None
    activReturn_1 = None
    activReturn_2 = None
    oper_f = None
    ord_st_f = None

        
    fields_df = ['item_id','client', 'id_sim__sim', 'id_sim__link', 'id_sim__type_sim', 'id_sim__operator', 'product', 'data_day', 'calls', 'countries', 'days', 'activation_date', 'order_status']

    product_choice_dict = dict(Orders.product.field.choices)
    data_choice_dict = dict(Orders.data_day.field.choices)
    status_choice_dict = dict(Orders.order_status.field.choices)
    
    orders_all = Orders.objects.filter(id_sim_id__isnull=False).filter(activation_date__gte=today).order_by('activation_date')
    
    orders_df = pd.DataFrame((orders_all.values(*fields_df)))
    orders_df['product'] = orders_df['product'].map(product_choice_dict)
    orders_df['data_day'] = orders_df['data_day'].map(data_choice_dict)
    orders_df['activation_date'] = pd.to_datetime(orders_df['activation_date'])
    orders_df['return_date'] = orders_df['activation_date'] + pd.to_timedelta(orders_df['days'], unit='d') - pd.to_timedelta(1, unit='d')
    
    orders_l = orders_df

    
    if request.method == 'GET':
        
        if request.GET.get('activGoing_1'): activGoing_1 = request.GET.get('activGoing_1')
        if request.GET.get('activGoing_2'): activGoing_2 = request.GET.get('activGoing_2')
        if request.GET.get('activReturn_1'): activReturn_1 = request.GET.get('activReturn_1')
        if request.GET.get('activReturn_2'): activReturn_2 = request.GET.get('activReturn_2')
        if request.GET.get('oper'): oper_f = request.GET.get('oper')
        if request.GET.get('ord_st'): ord_st_f = request.GET.get('ord_st')        

    if request.method == 'POST':

        if request.POST.get('activGoing_f'): activGoing_f = request.POST.get('activGoing_f')
        if request.POST.get('activReturn_f') : activReturn_f = request.POST.get('activReturn_f') 
        if request.POST.get('oper_f'): oper_f = request.POST.get('oper_f')
        if request.POST.get('ord_st_f'): ord_st_f = request.POST.get('ord_st_f')
        
        if activGoing_f is not None:
            activGoing = [item.strip() for item in activGoing_f.split('-')]
            activGoing_1 = dateF(activGoing[0])
            try: activGoing_2 = dateF(activGoing[1])
            except: pass
        
        if activReturn_f is not None:
            activReturn = [item.strip() for item in activReturn_f.split('-')]
            activReturn_1 = dateF(activReturn[0])
            try: activReturn_2 = dateF(activReturn[1])
            except: pass


        if 'up_status' in request.POST:
            ord_id = request.POST.getlist('ord_id')
            ord_s = request.POST.get('ord_staus')
            if ord_id and ord_s:
                for o_id in ord_id:
                    
                    order = Orders.objects.get(pk=o_id)
                    order.order_status = ord_s
                    order.save()
                    
                    order_id = order.order_id
                    order_st = order.order_status
                    order_plan = order.get_product_display()
                    try: type_sim = order.id_sim.type_sim
                    except: type_sim = 'esim'
                    apiStore = ApiStore.conectApiStore()
                    
                    if ord_s == 'CC' or ord_s == 'DS':
                        if order.id_sim:
                            # Update SIM
                            sim_put = Sims.objects.get(pk=order.id_sim.id)
                            if order.id_sim.type_sim == 'esim':
                                sim_put.sim_status = 'TC'
                                esim_v = True
                            else:
                                sim_put.sim_status = 'DS'
                            sim_put.sim_status = 'TC'
                            sim_put.save()
                                
                            # Delete SIM in Order
                            order_put = Orders.objects.get(pk=order.id)
                            order_put.id_sim_id = ''
                            order_put.save()
                            
                            # Deletar eSIM para site                            
                            if esim_v == True:    
                                updateEsimStore(order_id)
                        
                    # Save Notes
                    def addNote(t_note):
                        add_sim = Notes( 
                            id_item = Orders.objects.get(pk=order.id),
                            id_user = User.objects.get(pk=request.user.id),
                            note = t_note,
                            type_note = 'S',
                        )
                        add_sim.save()
                    
                    ord_status = Orders.order_status.field.choices
                    for st in ord_status:
                        if order_st == st[0] :    
                            addNote(f'Alterado de {st[1]} para {order.get_order_status_display()}')
                    
                    # Alterar status
                    # Status sis : Status Loja
                    status_sis_site = StatusSis.st_sis_site()
                    
                    if ord_s in status_sis_site:
                        update_store = {
                            'status': status_sis_site[ord_s]
                        }
                        apiStore.put(f'orders/{order.order_id}', update_store).json()
                    
                    # Enviar email
                    if ord_s == 'CN' and (type_sim == 'sim' or order_plan == 'USA'):
                        SendEmail.mailAction(id=order.id)
                        
                        addNote(f'E-mail enviado com sucesso!')
                        messages.success(request,'E-mail enviado com sucesso!')
                    
                messages.success(request,f'Pedido(s) atualizado com sucesso!')
            else:
                messages.info(request,f'Você precisa marcar alguma opção')        
    
        # End up_status / POST
    
    # FIlters ========================
    if activGoing_1 is not None:
        if activGoing_2 is not None:
            orders_l = orders_l[(orders_l['activation_date'] >= activGoing_1) & (orders_l['activation_date'] <= activGoing_2)]
            url_filter += f"&activGoing_1={activGoing_1}&activGoing_2={activGoing_2}"
        else:
            orders_l = orders_l[(orders_l['activation_date'] == activGoing_1)]
            url_filter += f"&activGoing_1={activGoing_1}"        

    if activReturn_1 is not None:
        if activReturn_2 is not None:
            orders_l = orders_l[(orders_l['return_date'] >= activReturn_1) & (orders_l['return_date'] <= activReturn_2)]
            url_filter += f"&activReturn_1={activReturn_1}&activReturn_2={activReturn_2}"
        else:
            orders_l = orders_l[(orders_l['return_date'] == activReturn_1)]
            url_filter += f"&activReturn_1={activReturn_1}"         
            
    if oper_f is not None:
        orders_l = orders_l[(orders_l['id_sim__operator'] == oper_f)]
        url_filter += f"&oper={oper_f}"

    if ord_st_f is not None:
        orders_l = orders_l[(orders_l['order_status'] == ord_st_f)]
        url_filter += f"&ord_st={ord_st_f}" 
    

    sims = Sims.objects.all()
    ord_status = Orders.order_status.field.choices
    oper_list = Sims.operator.field.choices

    # Listar status dos pedidos
    ord_st_list = []
    for ord_s in ord_status:
        ord = len(orders_l[orders_l['order_status'] == ord_s[0]])
        ord_st_list.append((ord_s[0],ord_s[1],ord))
        

    activList = orders_l.groupby(['id_sim__operator']).size().reset_index(name='countActiv')    
    countActivAll = countActivAll = activList['countActiv'].sum()
    try: countActivTM = activList[activList['id_sim__operator'] == 'TM']['countActiv'].values[0]
    except: countActivTM = 0
    try: countActivCM = activList[activList['id_sim__operator'] == 'CM']['countActiv'].values[0]
    except: countActivCM = 0
    try: countActivTC = activList[activList['id_sim__operator'] == 'TC']['countActiv'].values[0]
    except: countActivTC = 0
    
    # List
    orders_l = orders_l.to_dict('records')
    
    # Paginação
    paginator = Paginator(orders_l, 100)
    page = request.GET.get('page', 1)
    orders = paginator.get_page(page)

    
    context = {
        'orders_l': orders_l,
        'orders': orders,
        'sims': sims,
        'ord_st_list': ord_st_list,
        'oper_list': oper_list,
        'url_filter': url_filter,
        'status_choice_dict': status_choice_dict,
        'countActivAll': countActivAll,
        'countActivTM': countActivTM,
        'countActivCM': countActivCM,
        'countActivTC': countActivTC,
    }
    return render(request, 'painel/orders/activations.html', context)
    


# def textImg(request):
#     # Carrega a imagem em escala de cinza
#     img = cv2.imread('static/imei2.jpg', cv2.IMREAD_GRAYSCALE)
#     # Extrai o texto da imagem
#     texto = pytesseract.image_to_string(img)
#     textos = texto.split()
#     txt = []
#     for t in textos:
#         txt.append(f'{t}<br>')
    
#     return HttpResponse(txt)

# def esimExpSis(request):
    
        
#     apiStore = ApiStore.conectApiStore()
#     # Get the order
#     order_id = 54085
    
#     # Add the meta data
#     meta_data_list = {
#         "meta_data":[
#             {
#                 "key": "campo_esims",
#                 "value": "<img src='https://painel.acasadochip.com/media/8932042000002302486.jpeg' style='width: 300px; margin:40px;'><img src='https://painel.acasadochip.com/media/8932042000002302486.jpeg' style='width: 300px; margin:40px;'>"
#             },
#         ]
#     }

#     # Update the order
#     apiStore.put(f"orders/{order_id}", meta_data_list).json()    
#     return HttpResponse('eSIM enviado!')

# # def vendasSem(request):
# apiStore = conectApiStore()
# dateNow = datetime.datetime.now()  

# dateSem = datetime.datetime.now() - datetime.timedelta(days=7)
# print(dateSem)
# print(dateNow)
# vendasDaSemana = apiStore.get('reports/sales', params={'date_min': dateSem, 'date_max': dateNow})
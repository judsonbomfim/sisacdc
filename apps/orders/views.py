from django.contrib.auth.models import User
import os
import csv
from django.http import HttpResponse
from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from woocommerce import API
from django.utils.text import slugify
from apps.orders.models import Orders, Notes
from apps.sims.models import Sims

# Conect woocommerce api
def conectApiStore():
    wcapi = API(
        url = str(os.getenv('url_site')),
        consumer_key = str(os.getenv('consumer_key')),
        consumer_secret = str(os.getenv('consumer_secret')),
        wp_api = True,
        version = 'wc/v3',
        query_string_auth = True,
        timeout = 5000
    )
    return wcapi
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

def st_sis_site():
    status_sis_site = {
        'AE': 'agd-envio',
        'CC': 'cancelled',
        'MB': 'motoboy',
        'RS': 'reuso',
        'RT': 'retirada',
        'RE': 'reembolsar',
        'CN': 'completed',        
    }
    return status_sis_site

# Order list
@login_required(login_url='/login/')
def orders_list(request):
    global orders_l
    orders_l = ''
    
    orders_all = Orders.objects.all().order_by('-id')
    orders_l = orders_all
    
    if request.method == 'POST':
        if 'up_filter' in request.POST:
            name_f = request.POST['ord_name_f']
            if name_f != '': orders_l = orders_l.filter(client__icontains=name_f)
                
            order_f = request.POST['ord_order_f']
            if order_f != '': orders_l = orders_l.filter(item_id__icontains=order_f)
            
            sim_f = request.POST['ord_sim_f']
            if sim_f != '': orders_l = orders_l.filter(id_sim__sim__icontains=sim_f)
            
            oper_f = request.POST['oper_f']
            if oper_f != '': orders_l = orders_l.filter(id_sim__operator__icontains=oper_f)
            
            status_F = request.POST['ord_st_f']
            if status_F != '': orders_l = orders_l.filter(order_status__icontains=status_F)
                        
        if 'up_status' in request.POST:
            ord_id = request.POST.getlist('ord_id')
            ord_s = request.POST.get('ord_staus')
            if ord_id and ord_s:
                for o_id in ord_id:
                    order = Orders.objects.get(pk=o_id)
                    order.order_status = ord_s
                    order.save()
                    
                    # Alterar status
                    # Status sis : Status Loja
                    status_sis_site = st_sis_site()
                    
                    if ord_s in status_sis_site:
                        status_ped = {
                            'status': status_sis_site[ord_s]
                        }
                        apiStore = conectApiStore()                    
                        apiStore.put(f'orders/{order.order_id}', status_ped).json()
                    
                messages.success(request,f'Pedido(s) atualizado com sucesso!')
            else:
                messages.info(request,f'Você precisa marcar alguma opção')        
        
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
        'orders_l': orders_all,
        'orders': orders,
        'sims': sims,
        'ord_st_list': ord_st_list,
        'oper_list': oper_list,
    }
    return render(request, 'painel/orders/index.html', context)
    
# Store order details
@login_required(login_url='/login/')
def store_order_det(request,id):
    apiStore = conectApiStore()
    ord = apiStore.get(f'orders/{id}').json()
    
    context = {
        'ord': ord,
    }
    return render(request, 'painel/orders/details.html', context)

# Update orders
@login_required(login_url='/login/')
def ord_import(request):
    if request.method == 'GET':

        return render(request, 'painel/orders/import.html')    
       
    if request.method == 'POST':
        apiStore = conectApiStore()
        
        global n_item_total
        n_item_total = 0
        global msg_info
        msg_info = []
        global msg_error
        msg_error = []
        
        # Definir números de páginas
        per_page = 100
        order_p = apiStore.get('orders', params={'status': 'processing', 'per_page': per_page})
        total_pages = int(order_p.headers['X-WP-TotalPages'])
        n_page = 1
        
        while n_page <= total_pages:
            # Pedidos com status 'processing'
            ord = apiStore.get('orders', params={'order': 'asc', 'status': 'processing', 'per_page': per_page, 'page': n_page}).json()
                                    
            # Listar pedidos         
            for order in ord:
                n_item = 1
                
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
                                if i['value'] == 'Não': countries_i = False 
                                else: countries_i = True
                            if i['key'] == 'Data de Ativação': activation_date_i = dateF(i['value'])
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
                            msg_error.append(f'Pedido {order_id_i} atualizados com sucesso')                            
                        
                        # Alterar status
                        # Status sis : Status Loja
                        status_def_sis = {
                            'RT': 'retirada',
                            'MB': 'motoboy',
                            'RS': 'reuso',
                            'AG': 'agencia',
                            'AS': 'agd-envio',
                        }
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
        # global id_sim
        # id_sim = ''
        
        order = Orders.objects.get(pk=id)
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
        def insertSIM():
            sim_up = Sims.objects.filter(sim_status='DS', type_sim=type_sim, operator=operator).first()
            if sim_up:
                sim_put = Sims.objects.get(pk=sim_up.id)
                sim_put.sim_status = 'AT'
                sim_put.save()
                order_put = Orders.objects.get(pk=order.id)
                order_put.id_sim_id = sim_put.id
                order_put.save()
            else:       
                msg_error.append(f'Não há estoque de {operator} - {type_sim} no sistema')
            
        # Verificar se SIM já existe
        if sim:
            if operator != None and type_sim != None:            
                if order.id_sim:
                    # Alterar status no sistema e no site
                    updateSIM()
                    
                # Save SIMs
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
            else:
                msg_error.append(f'Você precisa selecionar o tipo de SIM e a Operadora')
        else:
            if order.id_sim:
                
                if (order.id_sim.operator != operator or order.id_sim.type_sim != type_sim) and (operator != None and type_sim != None):                
                    updateSIM()                    
                    insertSIM()
            else:
                if operator != None and type_sim != None:                 
                    insertSIM()
                else:
                    msg_error.append(f'Você precisa selecionar o tipo de SIM e a Operadora')
            
        # Update Order
        if activation_date == '':
            activation_date = order.activation_date
            
        # Save Note
        add_sim = Notes( 
            id_item = Orders.objects.get(pk=order.id),
            id_user = User.objects.get(pk=request.user.id),
            note = ord_note,
        )
        add_sim.save()
          
        
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
        
        # Alterar status
        # Status sis : Status Loja
        status_sis_site = st_sis_site()
        if ord_st in status_sis_site:
            status_ped = {
                'status': status_sis_site[ord_st]
            }
            apiStore = conectApiStore()                    
            apiStore.put(f'orders/{order.order_id}', status_ped).json()
    
        for msg_e in msg_error:
            messages.error(request,msg_e)
        for msg_o in msg_info:
            messages.info(request,msg_o)
        messages.success(request,f'Pedido {order.order_id} atualizado com sucesso!')
        return redirect('orders_list')

@login_required(login_url='/login/')
def ord_export_op(request):
    
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

        return response
            
    sims_op = Sims.operator.field.choices
    context= {
        'sims_op': sims_op,
    }
    
    return render(request, 'painel/orders/export_op.html', context)

# # def vendasSem(request):
# apiStore = conectApiStore()
# dateNow = datetime.datetime.now()  

# dateSem = datetime.datetime.now() - datetime.timedelta(days=7)
# print(dateSem)
# print(dateNow)
# vendasDaSemana = apiStore.get('reports/sales', params={'date_min': dateSem, 'date_max': dateNow})
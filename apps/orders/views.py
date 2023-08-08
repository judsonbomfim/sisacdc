import os
from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from woocommerce import API
from django.utils.text import slugify
from apps.orders.models import Orders
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
        timeout = 500
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


# Order list
def orders_list(request):
    if request.method == 'GET':
        orders_l = Orders.objects.all().order_by('id')
        orders_p = Orders.objects.all().order_by('id')
        sims = Sims.objects.all()
        ord_status = Orders.order_status.field.choices
        paginator = Paginator(orders_p, 50)
        page = request.GET.get('page')
        orders = paginator.get_page(page)
    
        context = {
            'orders_l': orders_l,
            'orders': orders,
            'sims': sims,
            'ord_status': ord_status,
        }
        return render(request, 'painel/orders/index.html', context)
    
    if request.method == 'POST':
        pass
    
# Store order details
def store_order_det(request,id):
    apiStore = conectApiStore()
    ord = apiStore.get(f'orders/{id}').json()
    
    context = {
        'ord': ord,
    }
    return render(request, 'painel/orders/details.html', context)

# Update orders
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
            print(f'Per_Page {total_pages}')
            # Pedidos com status 'processing'
            ord = apiStore.get('orders', params={'order': 'asc', 'status': 'processing', 'per_page': per_page, 'page': n_page}).json()
                                    
            # Listar pedidos         
            for order in ord:
                n_item = 1
                print(f'Item Listar')
                
                # Listar itens do pedido
                for item in order['line_items']:
                    
                    print(f'Item item')
                    
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
                            'AS': 'agd-envio',
                        }
                        status_ped = {
                            'status': status_def_sis[order_status_i]
                        }                                      
                        apiStore.put(f'orders/{order_id_i}', status_ped).json()    
                        
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
def ord_edit(request,id):
    if request.method == 'GET':
            
        order = Orders.objects.get(pk=id)
        context = {
            'order': order
        }
        return render(request, 'painel/orders/edit.html', context)
        
    if request.method == 'POST':
        
        global msg_info
        msg_info = []
        global msg_error
        msg_error = []
        global id_sim
        id_sim = ''
        
        order = Orders.objects.get(pk=id)
        type_sim = request.POST.get('type_sim')
        operator = request.POST.get('operator')
        sim = request.POST.get('sim')
        activation_date = request.POST.get('activation_date')
        cell_imei = request.POST.get('cell_imei')
        cell_eid = request.POST.get('cell_eid')
        tracking = request.POST.get('tracking')
        
        if order.id_sim_id != None and (order.id_sim.operator != operator or order.id_sim.type_sim != type_sim): 
            if sim == '':
                # Delete SIM           
                order_put = Orders.objects.get(pk=order.id)
                order_put.id_sim_id = ''
                order_put.save()
                
                # Update SIM
                sim_put = Sims.objects.get(pk=order.id_sim.id)
                sim_put.sim_status = 'TC'
                sim_put.save()
                
                # Insert SIM
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
            else:
                # Save SIMs
                add_sim = Sims(
                    sim = sim,
                    type_sim = type_sim,
                    operator = operator,
                    sim_status = 'AT',
                )
                add_sim.save()
                
                order_put = Orders.objects.get(pk=order.id)
                order_put.id_sim_id = add_sim.id
                order_put.save()  
            
        # Update Order
        if activation_date == '':
            activation_date = order.activation_date        
        
        order_put = Orders.objects.get(pk=id)
        order_put.activation_date = activation_date
        order_put.cell_imei = cell_imei
        order_put.cell_eid = cell_eid
        order_put.tracking = tracking
        order_put.save()
    
        for msg_e in msg_error:
            messages.error(request,msg_e)
        for msg_o in msg_info:
            messages.info(request,msg_o)
        messages.success(request,f'Pedido {order.order_id} atualizado com sucesso!')
        return redirect('orders_list')

# Orders Actions
def ord_actions(request, filter='all'):
    if request.method == 'POST':
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
                    status_def_sis = {
                        'AE': 'agd-envio',
                        'CC': 'cancelled',
                        'MB': 'motoboy',
                        'RS': 'reuso',
                        'RT': 'retirada',
                        'RE': 'reembolsar',
                    }
                    if ord_s in status_def_sis:
                        status_ped = {
                            'status': status_def_sis[ord_s]
                        }
                        apiStore = conectApiStore()                    
                        apiStore.put(f'orders/{order.order_id}', status_ped).json()   
                    
                messages.success(request,f'Pedido(s) atualizado com sucesso!')
            else:
                messages.info(request,f'Você precisa marcar alguma opção')

            return redirect('orders_list')
        
        if 'up_filter' in request.POST:
            orders_l = Orders.objects.all().order_by('id').filter()
            if request.POST['ord_staus_f'] == 'todos':
                orders_p = Orders.objects.all().order_by('id').filter()
            else:   
                orders_p = Orders.objects.all().order_by('id').filter(order_status=request.POST['ord_staus_f'])
            sims = Sims.objects.all()
            ord_status = Orders.order_status.field.choices
            paginator = Paginator(orders_p, 50)
            page = request.GET.get('page')
            orders = paginator.get_page(page)
        
            context = {
                'orders_l': orders_l,
                'orders': orders,
                'sims': sims,
                'ord_status': ord_status,
            }
            return render(request, 'painel/orders/index.html', context)

def ord_filters_st(request, filter='all'):
    pass

# # def vendasSem(request):
# apiStore = conectApiStore()
# dateNow = datetime.datetime.now()  

# dateSem = datetime.datetime.now() - datetime.timedelta(days=7)
# print(dateSem)
# print(dateNow)
# vendasDaSemana = apiStore.get('reports/sales', params={'date_min': dateSem, 'date_max': dateNow})
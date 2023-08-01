import datetime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import os
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
        orders = Orders.objects.all().order_by('id')
        sims = Sims.objects.all()
    
        context = {
            'orders': orders,
            'sims': sims,
        }
        return render(request, 'painel/orders/index.html', context)
    
# Store order details
def store_order_det(request,id):
    apiStore = conectApiStore()
    ord = apiStore.get(f'orders/{id}').json()
    context = {
        'ord': ord,
    }
    return render(request, 'painel/orders/details.html', context)

# Atualização de orders
def ord_update(request):
    if request.method == 'GET':

        return render(request, 'painel/orders/update.html')    
       
    if request.method == 'POST':
        apiStore = conectApiStore()
        
        global n_item_total
        n_item_total = 0
        global msg_sim
        msg_sim = []
        
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
                        # Definir status do pedido
                        if 'retirada' in shipping_i or 'motoboy' in shipping_i or condition_i == 'reuso-sim':
                            order_status_i = 'VS'
                        else:
                            order_status_i = 'PR'
                        # notes_i = 0
                        
                        # Definir variáveis para salvar no banco de dados                            
                        order_add = Orders(                    
                            order_id = order_id_i,
                            item_id = item_id_i,
                            client = client_i,
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
                            # notes = notes_i
                        )
                        
                        # Salvar itens no banco de dados
                        register = order_add.save()
                        register
                        # Id Pedido Loja
                        register_id = order_add.id                        
                        
                        # Alterar status na loja
                        # 'VS', 'Verificar SIM'
                        # 'AS', 'Atribuir SIM'
                        # 'RT', 'Retirada'
                        # 'MB', 'Motoboy'
                        status_ord = {
                            'VS': 'agd-envio',
                            'AS': 'agd-envio',
                            'RT': 'retirada',
                            'MB': 'motoboy',
                            'VS': 'agd-envio',
                        }
                        data = {
                            'status': status_ord[order_status_i]
                        }
                        apiStore.put(f'orders/{order_id_i}', data).json()
                        
                        # Alterar status do pedido para 'completed'
                        data = {
                            'status': 'agd-envio'
                        }
                        apiStore.put(f'orders/{order_id_i}', data).json()
                        
                        # Definir variáveis
                        q_i += 1 
                        n_item += 1
                        n_item_total += 1                        

                        # Add SIMs
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
                            # Status Atribuir SIM
                            order_status_i = 'AS'
                            
                            msg_sim.append(f'Não há estoque de {operator_i} - {type_sim_i} no sistema')
                            continue
                        
                        # update order
                        order_put = Orders.objects.get(pk=register_id)
                        order_put.id_sim_id = sim_ds.id
                        order_put.save()
                         
                        # update sim
                        sim_put = Sims.objects.get(pk=sim_ds.id)
                        sim_put.sim_status = 'AT'
                        sim_put.save()
            n_page += 1
            
                            
    # Mensagem de sucesso
    if n_item_total == 0:
        messages.info(request,'Não há pedido(s) para atualizar!')
    else:
        for msg in msg_sim:
            messages.error(request,msg)
        messages.success(request,'Pedido(s) atualizados com sucesso')        
    return render(request, 'painel/orders/update.html')


def ord_edit(request,id):
    order = Orders.objects.get(pk=id)
    context = {
        'order': order
    }
    return render(request, 'painel/orders/edit.html', context)

# # def vendasSem(request):
# apiStore = conectApiStore()
# dateNow = datetime.datetime.now()  

# dateSem = datetime.datetime.now() - datetime.timedelta(days=7)
# print(dateSem)
# print(dateNow)
# vendasDaSemana = apiStore.get('reports/sales', params={'date_min': dateSem, 'date_max': dateNow})
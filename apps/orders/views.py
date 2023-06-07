from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import os
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
        query_string_auth = True
    )
    return wcapi

# Date - 2023-05-16T18:40:27
def dateHour(dh):
    date = dh[0:10]
    hour = dh[11:19]
    date_hour = f'{date} {hour}-03'
    return date_hour
# Date - 17/06/2023
def dateF(d):
    dia = d[0:2]
    mes = d[3:5]
    ano = d[6:10]
    dataForm = f'{ano}-{mes}-{dia}'
    return dataForm

# Order list
def orders(request,id=1):
    apiStore = conectApiStore()
    if request.method == 'GET':
        ord = apiStore.get('orders', params={'per_page': 20, 'page': id})
        ord_list = ord.json()
        total_pages = int(ord.headers['X-WP-TotalPages'])

        context = {
            'ord': ord_list,
            'total_pages': total_pages,
        }
        return render(request, 'painel/orders/index.html', context)

# Order details
def order_det(request,id):
    apiStore = conectApiStore()
    ord = apiStore.get(f'orders/{id}').json()
    context = {
        'ord': ord,
    }
    return render(request, 'painel/orders/details.html', context)

# Atualização de orders
def ord_update(request):
    apiStore = conectApiStore()
       
    if request.method == 'GET':
        
        # Definir números de páginas
        per_page = 100
        order_p = apiStore.get('orders', params={'status': 'processing', 'per_page': per_page})
        total_pages = int(order_p.headers['X-WP-TotalPages'])
        
        # Pedidos com status 'processing'
        for p in range(total_pages):
            ord = apiStore.get('orders', params={'order': 'asc', 'status': 'processing', 'per_page': per_page, 'page': p+1}).json()
            
            # Listar Ordens         
            for order in ord:
                n_item = 1          
                
                # Listar itens do pedido
                for item in order['line_items']:
                    qtd = item['quantity']
                    q_i = 1
                    listTest = []
                    # Especificar produto a serem listados
                    if item['product_id'] == 50760 or item['product_id'] == 8873 or item['product_id'] == 8791 or item['product_id'] == 8761:
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
                            # Percorrer itens do pedido
                            for i in item['meta_data']:
                                if i['key'] == 'pa_tipo-de-sim': tipo_sim_i = i['value']
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
                            order_status_i = 'PR'
                            notes_i = 0
                            
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
                                notes = notes_i
                            )
                            
                            # Salvar itens no banco de dados
                            order_add.save()
                            # Esvaziar variáveis
                            locals().clear()
                            # Incrementar variáveis
                            n_item += 1
                            q_i += 1
                                        
        context = {
            'ord': 'Tudo certo!',
        }   
        return render(request, 'painel/orders/update.html', context)
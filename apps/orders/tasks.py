from django.contrib.auth.models import User
from celery import shared_task
from django.utils.text import slugify
from datetime import datetime, timedelta
from .classes import ApiStore, StatusSis, DateFormats
from apps.orders.models import Orders, Notes
from apps.sims.models import Sims
from apps.voice_calls.models import VoiceCalls, VoiceNumbers
import getpass
import time
from apps.sims.tasks import sims_in_orders
from apps.send_email.tasks import send_email_sims
from apps.voice_calls.tasks import number_in_voice

@shared_task
def order_import():
    # Importar pedidos
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
                    order_date_i = DateFormats.dateHour(order['date_created'])
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
                    
                    id_user = None
                    if getpass.getuser():
                        id_user = getpass.getuser()
                    
                    # Save Notes
                    add_sim = Notes( 
                        id_item = Orders.objects.get(pk=order_add.id),
                        id_user = None,
                        note = f'Pedido importado para o sistema',
                        type_note = 'S',
                    )
                    add_sim.save()
                    
                    # Insert Voice Calls
                    if calls_i == True:
                        
                        add_voice = VoiceCalls(
                            id_item = order_add,
                            status = 'PR'
                        )
                        add_voice.save()
                    
                        # Save Notes
                        add_sim = Notes( 
                            id_item = Orders.objects.get(pk=order_add.id),
                            id_user = None,
                            note = f'Chamada de Voz Criada',
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
    
    # Status 
    if n_item_total == 0:
        print('>>>>>>>>>>>>>>>>>>>>>>> Não há pedido(s) para atualizar!')
    else:
        print('>>>>>>>>>>>>>>>>>>>>>>> Pedidos importados com sucesso')

@shared_task
def orders_auto():
    print('-----------------orders_auto')
    order_import.delay()
    time.sleep(20)
    sims_in_orders.delay()
    time.sleep(20)
    send_email_sims.delay()
    time.sleep(20)
    number_in_voice.delay()

@shared_task
def orders_up_status(ord_id, ord_s, id_user):
    
    print('-----------------ord_id, ord_s, id_user')
    print(ord_id, ord_s, id_user)

    ord_id = ord_id
    ord_s = ord_s
    
    for o_id in ord_id:
        
        print('-----------------o_id')
        print(o_id)
        
        order = Orders.objects.get(pk=o_id)
        user = User.objects.get(pk=id_user)
        
        order_id = order.id
        order_st = order.order_status
        order_plan = order.get_product_display()
        try: type_sim = order.id_sim.type_sim
        except: type_sim = 'esim'
        apiStore = ApiStore.conectApiStore()

        # Save status System
        order.order_status = ord_s
        order.save()
        
        if ord_s == 'CC' or ord_s == 'DS':
            if order.id_sim:
                # Update SIM
                sim_put = Sims.objects.get(pk=order.id_sim.id)
                if order.id_sim.type_sim == 'esim':
                    sim_put.sim_status = 'TC'
                    # Deletar eSIM para site                            
                    ApiStore.updateEsimStore(order_id)
                else:
                    sim_put.sim_status = 'DS'
                sim_put.sim_status = 'TC'
                sim_put.save()
                    
                # Delete SIM in Order
                order_put = Orders.objects.get(pk=order_id)
                order_put.id_sim_id = ''
                order_put.save()
                
                if order.calls == True and VoiceCalls.objects.get(id_item=order_id).DoesNotExist:
                    voice_d = VoiceCalls.objects.get(id_item=order_id)
                    num_s = VoiceNumbers.objects.get(id=voice_d.id_number)
                    
                    num_s.number_status = 'DS'
                    num_s.save()                  
                    
                    voice_d.delete()

        # Status sis : Status Loja
        status_sis_site = StatusSis.st_sis_site()
        
        if ord_s in status_sis_site:
            update_store = {
                'status': status_sis_site[ord_s]
            }
            apiStore.put(f'orders/{order.order_id}', update_store).json()
        
        # Save Notes
        def addNote(t_note):
            add_sim = Notes( 
                id_item = Orders.objects.get(pk=order.id),
                id_user = user,
                note = t_note,
                type_note = 'S',
            )
            add_sim.save()
        
        ord_status = Orders.order_status.field.choices
        for st in ord_status:
            if order_st == st[0] :
                addNote(f'Alterado de {st[1]} para {order.get_order_status_display()}')
        
        # Enviar email
        if ord_s == 'CN' and (type_sim == 'sim' or order_plan == 'USA'):
            send_email_sims.delay(id=order.id)

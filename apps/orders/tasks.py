from django.contrib.auth.models import User
from celery import shared_task
from django.utils.text import slugify
from .classes import ApiStore, StatusStore, DateFormats, UpdateStore
from apps.orders.models import Orders, Notes
from apps.sims.models import Sims
from apps.voice_calls.models import VoiceCalls, VoiceNumbers
import time, requests
from apps.sims.tasks import sims_in_orders, simDeactivateTC
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

    # Pedidos com status 'processing'
    response = apiStore.get('orders', params={'order': 'asc', 'status': 'processing'})
    try:
        ord = response.json()            
    except Exception as e:
        print(f"Erro ao decodificar JSON da resposta da API: {e}")
        print(f"Status code: {response.status_code}, Conteúdo: {response.text}")
        return
    
    # Listar pedidos         
    for order in ord:
        
        # Verificar se order é válido (dicionário com ID)
        if not isinstance(order, dict) or 'id' not in order:
            print(f"Sem itens para importar")
            continue
            
        n_item = 1
        id_ord = order["id"]
                
        # Verificar pedido repetido - se order_id já existe, pula
        if Orders.objects.filter(order_id=id_ord).exists():
            print(f'Pedido {id_ord} já importado, pulando')
            continue
        
        # Listar itens do pedido
        for item in order['line_items']:

            # Especificar produtos que NÃO serão listados
            prod_sel = [
                8901,   # Chamada de Voz
                44505,  # Franquia Adicional
                44549,  # Alteração de Frete
                47058,  # Troca de Chip
                68666,  # Dia Adicional
                ]
            if item['product_id'] in prod_sel:
                continue
                        
            qtd = item['quantity']
            q_i = 1 
            
            print(f'---------- Importando pedido {id_ord}')            
            
            while q_i <= qtd:
                order_id_i = order['id']
                item_id_i = f'{order_id_i}-{n_item}'
                item_id_store_i = item['id']
                client_i = f'{order["billing"]["first_name"]} {order["billing"]["last_name"]}'
                email_i = order['billing']['email']
                if "Global" in item['name']:
                    product_i = 'chip-internacional-global'
                else:
                    product_i = slugify(item['name'])
                
                qty_i = 1
                if order['coupon_lines']:
                    coupon_i = order['coupon_lines'][0]['code']
                else: 
                    coupon_i = '-'
                
                # Definir valor padrão para variáveis
                ord_chip_nun_i = '-'
                condition_i = 'novo-sim'
                calls_i = False
                countries_i = False
                activation_date_i = '2001-01-01'
                data_day_i = '1gb'
                cell_mod_i = False
                celular_samsung_i = False
                type_sim_i = 'sim'
                days_i = '0'
                
                # Percorrer itens do pedido
                for i in item['meta_data']:
                    if i['key'] == '_tipo_chip': 
                        type_sim_i = i['value']
                    if i['key'] == '_condicao_chip': 
                        if i['value'] == 'novo':
                            condition_i = 'novo-sim'
                    if i['key'] == '_agencia_cadastrada':
                        condition_i = 'reuso-sim'
                    if i['key'] == '_numero_sim':
                        ord_chip_nun_i = i['value']
                    if i['key'] == 'pa_dados-diarios': 
                        data_day_i = i['value']
                    if i['key'] == 'pa_dias': 
                        days_i = i['value']
                    if i['key'] == '_plano_voz': 
                        if i['value'] == '1':
                            calls_i = True
                    if i['key'] == '_china_hongkong_taiwan':
                        countries_i = True if i['display_value'] == 'Sim' else False
                    if i['key'] == '_data_ativacao': 
                        activation_date_i = i['value']
                    if i['key'] == '_celular_samsung': 
                        celular_samsung_i = True
                
                shipping_i = order['shipping_lines'][0]['method_title']
                order_date_i = DateFormats.dateHour(order['date_created'])
                
                # Definir status do pedido
                if 'RETIRADA' in shipping_i.upper():
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
                
                if activation_date_i == '2001-01-01':
                    order_status_i = 'EI'
                if product_i == 'chip-internacional-eua-30-dias':
                    calls_i = False
                    
                shipping_i = shipping_i[:40]

                # USO DE get_or_create - EVITA DUPLICAÇÃO
                obj, created = Orders.objects.get_or_create(
                    item_id=item_id_i,
                    defaults={
                        'order_id': order_id_i,
                        'item_id_store': item_id_store_i,
                        'client': client_i,
                        'email': email_i,
                        'product': product_i,
                        'data_day': data_day_i,
                        'qty': qty_i,
                        'coupon': coupon_i,
                        'condition': condition_i,
                        'days': days_i,
                        'calls': calls_i,
                        'countries': countries_i,
                        'cell_mod': cell_mod_i,
                        'ord_chip_nun': ord_chip_nun_i,
                        'shipping': shipping_i,
                        'order_date': order_date_i,
                        'activation_date': activation_date_i,
                        'order_status': order_status_i,
                        'type_sim': type_sim_i,
                        'celular_samsung': celular_samsung_i,
                    }
                )
                
                # SÓ PROCESSA SE FOR NOVO
                if created:
                    print(f'>>>>>>>>>> Importando pedido {order_id_i} - item {item_id_i}')
                    
                    # Save Notes
                    Notes.objects.create(
                        id_item=obj,
                        id_user=None,
                        note='Pedido importado para o sistema',
                        type_note='S',
                    )
                    
                    if activation_date_i == '2001-01-01':
                        Notes.objects.create(
                            id_item=obj,
                            id_user=None,
                            note='Pedido sem data de ativação. Verificar com cliente.',
                            type_note='S',
                        )
                    
                    # Insert Voice Calls
                    if calls_i:
                        VoiceCalls.objects.create(
                            id_item=obj,
                            days=days_i,
                            activation_date=activation_date_i,
                            call_status='PR'
                        )
                        
                        Notes.objects.create(
                            id_item=obj,
                            id_user=None,
                            note='Chamada de Voz Criada',
                            type_note='S',
                        )
                    
                    # Atualizar site
                    UpdateStore.upStore(
                        order_id=order_id_i,
                        item_id_store=item_id_store_i if item_id_store_i else None, 
                        _data_ativacao=activation_date_i if activation_date_i else None,
                        _status=order_status_i if order_status_i else None,
                        status_g=order_status_i if order_status_i else None,
                    )
                    
                    n_item_total += 1
                    msg_info.append(f'Pedido {order_id_i} importado com sucesso')
                else:
                    print(f'Item já existe: {item_id_i}, pulando')
                
                # Definir variáveis
                q_i += 1 
                n_item += 1
                    
    # Status 
    if n_item_total != 0:
        print('>>>>>>>>>>>>>>>>>>>>>>> Pedidos importados com sucesso')


@shared_task
def order_import_voice():
    # Importar pedidos
    apiStore = ApiStore.conectApiStore()
    
    global n_item_total
    n_item_total = 0
    global msg_info
    msg_info = []
    global msg_error
    msg_error = []
       
    # Pedidos com status 'processing'
    response = apiStore.get('orders', params={'order': 'asc', 'status': 'processing'})
    try:
        ord = response.json()            
    except Exception as e:
        print(f"Erro ao decodificar JSON da resposta da API: {e}")
        print(f"Status code: {response.status_code}, Conteúdo: {response.text}")
        return
    
    # Listar pedidos         
    for order in ord:
        
        # Verificar se order é válido (dicionário com ID)
        if not isinstance(order, dict) or 'id' not in order:
            continue
        
        n_item = 1
        id_ord = order["id"]

        # Verificar pedido repetido
        if Orders.objects.filter(order_id=id_ord).exists():
            print(f'Pedido {id_ord} já importado, pulando')
            continue
        
        # Verificar se line_items existe
        if 'line_items' not in order:
            continue
        
        # Listar itens do pedido
        for item in order['line_items']:
                                
            # Especificar produtos a serem listados
            prod_sel = [8901]
            if item['product_id'] not in prod_sel:
                continue
                            
            qtd = item['quantity']
            q_i = 1 
            
            print(f'---------- Importando pedido {id_ord}')
            
            while q_i <= qtd:
                order_id_i = order['id']
                item_id_i = f'{order_id_i}-{n_item}'
                item_id_store_i = item['id']
                client_i = f'{order["billing"]["first_name"]} {order["billing"]["last_name"]}'
                email_i = order['billing']['email']
                product_i = slugify(item['name'])
                qty_i = 1
                if order['coupon_lines']:
                    coupon_i = order['coupon_lines'][0]['code']
                else: 
                    coupon_i = '-'
                
                # Definir valor padrão para variáveis
                ord_chip_nun_i = '-'
                countries_i = False
                cell_mod_i = False
                condition_i = "novo-sim"
                activation_date_i = '2001-01-01'
                data_day_i = 'ilimitado'
                type_sim_i = 'sim'  # default
                days_i = '0'  # default
                
                # Percorrer itens do pedido
                for i in item['meta_data']:
                    if i['key'] == 'pa_dias': 
                        days_i = i['value']
                    if i['key'] == '_data_ativacao': 
                        activation_date_i = i['value']
                    if i['key'] == '_numero_sim': 
                        ord_chip_nun_i = i['value']
                
                shipping_i = 'Sem Frete'
                order_date_i = DateFormats.dateHour(order['date_created'])
                calls_i = True
         
                if activation_date_i == '2001-01-01':
                    order_status_i = 'EI'
                else:
                    order_status_i = 'PV'
                    
                # Se for um plano EUA 30 dias
                if product_i == 'chip-internacional-eua-30-dias':
                    calls_i = False
                
                # USO DE get_or_create - EVITA DUPLICAÇÃO
                obj, created = Orders.objects.get_or_create(
                    item_id=item_id_i,
                    defaults={
                        'order_id': order_id_i,
                        'item_id_store': item_id_store_i,
                        'client': client_i,
                        'email': email_i,
                        'product': product_i,
                        'data_day': data_day_i,
                        'qty': qty_i,
                        'coupon': coupon_i,
                        'condition': condition_i,
                        'days': days_i,
                        'calls': calls_i,
                        'countries': countries_i,
                        'cell_mod': cell_mod_i,
                        'ord_chip_nun': ord_chip_nun_i,
                        'shipping': shipping_i,
                        'order_date': order_date_i,
                        'activation_date': activation_date_i,
                        'order_status': order_status_i,
                        'type_sim': type_sim_i,
                    }
                )
                
                # SÓ PROCESSA SE FOR NOVO
                if created:
                    print(f'>>>>>>>>>> Importando pedido {order_id_i} - item {item_id_i}')
                    
                    # Save Notes
                    Notes.objects.create(
                        id_item=obj,
                        id_user=None,
                        note='Pedido importado para o sistema',
                        type_note='S',
                    )
                    
                    if activation_date_i == '2001-01-01':
                        Notes.objects.create(
                            id_item=obj,
                            id_user=None,
                            note='Pedido sem data de ativação. Verificar com cliente.',
                            type_note='S',
                        )
                    
                    # Insert Voice Calls
                    if calls_i:
                        VoiceCalls.objects.create(
                            id_item=obj,
                            days=days_i,
                            activation_date=activation_date_i,
                            call_status='PR'
                        )
                        
                        Notes.objects.create(
                            id_item=obj,
                            id_user=None,
                            note='Chamada de Voz Criada',
                            type_note='S',
                        )
                    
                    # Alterar status
                    if order_status_i in StatusStore.st_sis_site():
                        UpdateStore.upStore(
                            order_id=order_id_i,
                            item_id_store=item_id_store_i if item_id_store_i else None,
                            _status=order_status_i if order_status_i else None,
                            status_g=order_status_i if order_status_i else None,
                        )
                    
                    n_item_total += 1
                    msg_info.append(f'Pedido {order_id_i} importado com sucesso')
                else:
                    print(f'Item já existe: {item_id_i}, pulando')

                # Definir variáveis
                q_i += 1 
                n_item += 1
                    
    # Status 
    if n_item_total != 0:
        print('>>>>>>>>>>>>>>>>>>>>>>> Pedidos importados com sucesso')


@shared_task
def orders_auto():
    print('-----------------orders_auto')
    order_import.delay()
    time.sleep(10)
    order_import_voice.delay()
    time.sleep(10)
    sims_in_orders.delay()
    time.sleep(10)
    number_in_voice.delay()
    time.sleep(10)
    send_email_sims.delay()


@shared_task
def orders_up_status(ord_id, ord_s, id_user, ord_s_prev=None):
    
    # Verificar se ord_id é uma lista
    if not isinstance(ord_id, list):
        ord_id = [ord_id]
    
    for o_id in ord_id:
        
        if o_id is None:
            print(f"Item de pedido inválido ou sem ID: {order}")
            continue
               
        order = Orders.objects.get(pk=o_id)
        user = User.objects.get(pk=id_user)
        order_id = order.id
        order_st = order.order_status
        order_plan = order.get_product_display()
        try: type_sim = order.id_sim.type_sim
        except: type_sim = 'esim'

        # Save status System
        order.order_status = ord_s
        order.save()
        
        # Desativar (e)SIM
        if (ord_s == 'CC' or ord_s == 'DE' or ord_s == 'RE'):
            if order.id_sim:                
                # Change TC                
                if (order.id_sim.operator == 'TI' or order.id_sim.operator == 'TC') and ord_s == 'DE':
                    print('----------------- Alterar/desativar TC/TI -----------------')
                    simDeactivateTC(id=order.id)
                
                if ord_s_prev != 'ED':
                    # Update SIM
                    sim_put = Sims.objects.get(pk=order.id_sim.id)
                    sim_put.sim_status = 'DE'
                    sim_put.save()
            
                
            # Edit Voice
            if order.calls == True and VoiceCalls.objects.get(id_item=order_id).DoesNotExist:
                voice_d = VoiceCalls.objects.get(id_item=order_id)
                if voice_d.id_number:
                    num_s = VoiceNumbers.objects.get(id=voice_d.id_number.id)                
                    num_s.number_status = 'DS'
                    num_s.save()                
                    # voice_d.delete()
        
        # Verificar se todos os itens estão cancelados
        order_ver = Orders.objects.filter(order_id=order.order_id)

        order_canc = 0
        for ord_v in order_ver:
            if ord_v.order_status != 'CC':
                order_canc += 1 
        
        order_reemb = 0
        # Verificar se todos os itens estão reembolsados
        for ord_v in order_ver:
            if ord_v.order_status != 'RB':
                order_reemb += 1 
        
        # Só cancelar se todos os itens estiverem cancelados / reembolsados
        if (order_canc == 0 and ord_s == 'CC') or (order_reemb == 0 and ord_s == 'RB') or ord_s != 'DE':
            print('--------------------------- Alterar STATUS Loja')        
            if ord_s in StatusStore.st_sis_site():
                UpdateStore.upStore(
                    order_id = order.order_id,
                    item_id_store = order.item_id_store if order.item_id_store else None,
                    _status = ord_v.order_status if ord_v.order_status else None,
                    status_g = ord_s if ord_s else None,
                ) 
        elif ord_s not in ['CC', 'RB', 'DE']:
            print('--------------------------- Alterar STATUS Loja')        
            UpdateStore.upStore(
                order_id = order.order_id,
                item_id_store = order.item_id_store if order.item_id_store else None,
                _status = ord_s if ord_s else None,
                status_g = ord_s if ord_s else None,
            )
        elif ord_s == 'CC':
            # Cancelar só os itens
            UpdateStore.upStore(
                order_id = order.order_id,
                item_id_store = order.item_id_store if order.item_id_store else None,
                _status = ord_s if ord_s else None,
                status_g = ord_s if ord_s else None,
            )
        
        # Enviar e-mail de ativação
        if ord_s == 'AA':
            send_email_sims.delay(id=order.id)           

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
        if order_st != 'ED':
            try:
                old_status = ord_status.get(order_st, f'Status {order_st} desconhecido')
                new_status = ord_status.get(ord_s, f'Status {ord_s} desconhecido')
                addNote(f'Alterado de {old_status} para {new_status}')
                print(f"Nota gravada: Alterado de {old_status} para {new_status}")  # Log temporário
            except Exception as e:
                print(f"Erro ao gravar nota: {e}")  # Log do erro
            
        # Enviar email
        if ord_s == 'CN' and (type_sim == 'sim' or order_plan == 'USA'):
            send_email_sims.delay(id=order.id)


# @shared_task
# def update_st():
    
#     total_ord = 0
    
#     # Importar pedidos   
#     while True:
#         from datetime import date
#         try:
#             data_inicio = date(2025, 8, 10)  # exemplo de data

#             ord = Orders.objects.filter(order_date__gte=data_inicio)
#             print('ORD >>>>>>>>>> ',ord)
            
#             # Se não houver mais pedidos, sair do loop
#             if not ord:
#                 break
#         except requests.exceptions.RequestException as e:
#             print(f"Erro ao obter pedidos na página {n_page}: {e}")
#             break
#         except ValueError as e:
#             print(f"Erro ao decodificar JSON na página {n_page}: {e}")
#             break

#         # Listar pedidos         
#         for order_store in ord:
#             n_item = 1
#             id_ord = order_store.id            
#             id_sis = Orders.objects.filter(id=id_ord).first()
            
#             if id_sis != None:
#                 order_id = id_sis.order_id
#                 order_status = id_sis.order_status
#                 UpdateStore.upStore(order_id, _status='AT', status_g='AT')                
#                 total_ord += 1
#                 print(f'>>>>>>>>>> Pedidos {id_ord} = TOTAL {total_ord}')

#         n_page += 1

#     print(f'Total de pedidos processados: {total_ord}')
    
    
@shared_task(time_limit=300)
def update_st(*args, **kwargs):
    # Importar pedidos
    apiStore = ApiStore.conectApiStore()
    
    # Definir números de páginas
    per_page = 100
    n_page = 1
    total_ord = 0
    
    while True:
        try:
            # Pedidos no site com status "aguardando"
            response = apiStore.get('orders', params={'order': 'desc', 'status': 'on-hold', 'per_page': per_page, 'page': n_page})
            response.raise_for_status()
            
            # Verificar se a resposta contém dados
            if response.text.strip() == "":
                print(f"Resposta vazia na página {n_page}")
                break
            
            ord = response.json()
            
            # Se não houver mais pedidos, sair do loop
            if not ord:
                break
        except requests.exceptions.RequestException as e:
            print(f"Erro ao obter pedidos na página {n_page}: {e}")
            break
        except ValueError as e:
            print(f"Erro ao decodificar JSON na página {n_page}: {e}")
            break

        # Listar pedidos         
        for order_store in ord:
            time.sleep(1)
            n_item = 1
            id_ord = order_store["id"]
            
            id_sis = Orders.objects.filter(order_id=id_ord).first()
            
            if id_sis != None:
                id_order = id_sis.id
                order_status = id_sis.order_status                

                UpdateStore.upStore(
                    order_id = id_ord,
                    status_g = order_status if order_status else None,
                )                    

                total_ord += 1
                print(f'>>>>>>>>>> Pedidos {id_ord} - {order_status} = TOTAL {total_ord}')

        n_page += 1

    print(f'Total de pedidos processados: {total_ord}')
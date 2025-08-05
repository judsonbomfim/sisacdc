from django.contrib.auth.models import User
from celery import shared_task
from django.utils.text import slugify
from .classes import ApiStore, StatusStore, DateFormats
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
    
    # Definir números de páginas
    per_page = 100
    order_p = apiStore.get('orders', params={'status': 'processing', 'per_page': per_page})        
    
    try:
        total_pages = int(order_p.headers.get('X-WP-TotalPages', 1))
    except Exception as e:
        print(f"Header X-WP-TotalPages não encontrado ou inválido: {e}")
        total_pages = 1
    n_page = 1
    
    # orders_all = Orders.objects.all()
    
    while n_page <= total_pages:
        # Pedidos com status 'processing'
        response = apiStore.get('orders', params={'order': 'asc', 'status': 'processing', 'per_page': per_page, 'page': n_page})
        try:
            ord = response.json()
        except Exception as e:
            print(f"Erro ao decodificar JSON da resposta da API: {e}")
            print(f"Status code: {response.status_code}, Conteúdo: {response.text}")
            break  # ou continue, dependendo do fluxo desejado
        
        # Listar pedidos         
        for order in ord:
            n_item = 1
            id_ord = order["id"]
            
            print(f'---------- Importando pedido {id_ord}')
            
            # Verificar pedido repetido
            id_sis = Orders.objects.filter(order_id=id_ord)
            if id_sis:
                # Se o pedido já foi importado, atualizar status
                status_sis = id_sis.first().order_status
                status_sis_site = StatusStore.st_sis_site()
                up_order_st_store(id_ord,status_sis_site[status_sis])
                print(f'---------- Pedido {id_ord} já importado. Status: {status_sis_site[status_sis]}')
                continue
            else: pass
            
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
                
                while q_i <= qtd:
                    order_id_i = order['id']
                    print(f'---------- Importando item {order_id_i}')
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
                    else: coupon_i = '-'
                    # Definir valor padrão para variáveis
                    ord_chip_nun_i = '-'
                    countries_i = False
                    cell_mod_i = False
                    activation_date_i = False
                    # Percorrer itens do pedido
                    for i in item['meta_data']:
                        if i['key'] == 'pa_tipo-de-sim': type_sim_i = i['value']
                        if i['key'] == 'pa_condicao-do-chip': condition_i = i['value']
                        if i['key'] == 'pa_dados-diarios': data_day_i = i['value']
                        if i['key'] == 'pa_dias': days_i = i['value']
                        if i['key'] == 'pa_plano-de-voz': 
                            if i['value'] == 'sem-ligacoes': calls_i = False
                            else: calls_i = True
                        if 'Visitará' in i['key']: ## VERIFICAR SITE NOVO ##
                            if i['display_value'] == 'Sim': countries_i = True
                            else: countries_i = False
                        if i['key'] == '_data_ativacao': 
                            activation_date_i = i['value']
                        if i['key'] == '_numero_sim': ord_chip_nun_i = i['value']
                    if activation_date_i == False:
                            activation_date_i = '0001-01-01'
                    shipping_i = order['shipping_lines'][0]['method_title']
                    order_date_i = DateFormats.dateHour(order['date_created'])
                    # notes_i = 0
                    
                    print(f'---------- Definindo status Loja')
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
                    elif activation_date_i == '0001-01-01':
                        order_status_i = 'EI'
                    else:
                        order_status_i = 'AS'
                        
                        
                    # Se for um plano EUA 30 dias
                    if product_i == 'chip-internacional-eua-30-dias':
                        calls_i = False             
                    
                    # Definir variáveis para salvar no banco de dados                            
                    order_add = Orders(                    
                        order_id = order_id_i,
                        item_id = item_id_i,
                        item_id_store = item_id_store_i,
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
                    

                    try:
                        register = order_add.save()
                        register
                    except Exception as e:
                        print(f'Pedido {order_id_i} deu um erro ao importar: {e}')
                        continue
                    
                    # id_user = None
                    # if getpass.getuser():
                    #     id_user = getpass.getuser()
                    
                    # Save Notes
                    add_sim = Notes( 
                        id_item = Orders.objects.get(pk=order_add.id),
                        id_user = None,
                        note = f'Pedido importado para o sistema',
                        type_note = 'S',
                    )
                    add_sim.save()
                    
                    if activation_date_i == '0001-01-01':
                        add_sim = Notes( 
                            id_item = Orders.objects.get(pk=order_add.id),
                            id_user = None,
                            note = f'Pedido sem data de ativação. Verificar com cliente.',
                            type_note = 'S',
                        )
                        add_sim.save()
                    
                    # Insert Voice Calls
                    if calls_i == True:
                        
                        add_voice = VoiceCalls(
                            id_item = Orders.objects.get(pk=order_add.id),
                            call_status = 'PR'
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
                    status_def_sis = StatusStore.st_sis_site()
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
def order_import_voice():
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
    order_p = apiStore.get('orders', params={'status': 'processing', 'per_page': per_page})        
    
    try:
        total_pages = int(order_p.headers.get('X-WP-TotalPages', 1))
    except Exception as e:
        print(f"Header X-WP-TotalPages não encontrado ou inválido: {e}")
        total_pages = 1
        
    n_page = 1
    
    # orders_all = Orders.objects.all()
    
    while n_page <= total_pages:
        # Pedidos com status 'processing'
        response = apiStore.get('orders', params={'order': 'asc', 'status': 'processing', 'per_page': per_page, 'page': n_page})
        try:
            ord = response.json()
        except Exception as e:
            print(f"Erro ao decodificar JSON da resposta da API: {e}")
            print(f"Status code: {response.status_code}, Conteúdo: {response.text}")
            break  # ou continue
        
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
                prod_sel = [8901]
                if item['product_id'] not in prod_sel:
                    continue
                                
                qtd = item['quantity']
                q_i = 1 
                
                while q_i <= qtd:
                    order_id_i = order['id']
                    item_id_i = f'{order_id_i}-{n_item}'
                    item_id_store_i = item['id']
                    client_i = f'{order["billing"]["first_name"]} {order["billing"]["last_name"]}'
                    email_i = order['billing']['email']
                    product_i = slugify(item['name']) # Definir nome do produto                    
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
                        type_sim_i = 'sim'
                        condition_i = "novo-sim"
                        data_day_i = 'ilimitado'
                        if i['key'] == 'pa_dias': days_i = i['value']
                        calls_i = True
                        countries_i = False
                        if i['key'] == 'Data de Ativação': 
                            if i['value'] == None or i['value'] == '': 
                                activation_date_i = '0001-01-01'
                            else:
                                activation_date_i = i['value']
                        if i['key'] == 'Modelo e marca de celular': cell_mod_i = i['value']
                        ord_chip_nun_i = '---'
                    shipping_i = 'Sem Frete'
                    order_date_i = DateFormats.dateHour(order['date_created'])
                    # notes_i = 0
                    
                    if activation_date_i == '0001-01-01':
                        order_status_i = 'EI'
                    else:
                        order_status_i = 'PV'
                        
                        
                    # Se for um plano EUA 30 dias
                    if product_i == 'chip-internacional-eua-30-dias':
                        calls_i = False             
                    
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
                    
                    # id_user = None
                    # if getpass.getuser():
                    #     id_user = getpass.getuser()
                    
                    # Save Notes
                    add_sim = Notes( 
                        id_item = Orders.objects.get(pk=order_add.id),
                        id_user = None,
                        note = f'Pedido importado para o sistema',
                        type_note = 'S',
                    )
                    add_sim.save()
                    
                    if activation_date_i == '0001-01-01':
                        add_sim = Notes( 
                            id_item = Orders.objects.get(pk=order_add.id),
                            id_user = None,
                            note = f'Pedido sem data de ativação. Verificar com cliente.',
                            type_note = 'S',
                        )
                        add_sim.save()
                    
                    # Insert Voice Calls
                    if calls_i == True:
                        
                        add_voice = VoiceCalls(
                            id_item = Orders.objects.get(pk=order_add.id),
                            days = days_i,
                            activation_date = activation_date_i,
                            call_status = 'PR'
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
                    status_def_sis = StatusStore.st_sis_site()
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
    time.sleep(5)
    order_import_voice.delay()
    time.sleep(5)
    sims_in_orders.delay()
    time.sleep(5)
    number_in_voice.delay()
    time.sleep(10)
    send_email_sims.delay()

@shared_task
def orders_up_status(ord_id, ord_s, id_user, ord_s_prev=None):
    
    # Verificar se ord_id é uma lista
    if not isinstance(ord_id, list):
        ord_id = [ord_id]

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
        
        # Desativar (e)SIM
        if (ord_s == 'CC' or ord_s == 'DE' or ord_s == 'RE'):
            if order.id_sim:                
                # Change TC
                if (order.id_sim.operator == 'TI' or order.id_sim.operator == 'TC') and ord_s_prev != 'ED':
                    simDeactivateTC(id=order.id)
                
                if ord_s_prev != 'ED':
                    # Update SIM
                    sim_put = Sims.objects.get(pk=order.id_sim.id)
                    sim_put.sim_status = 'DE'
                    sim_put.save()
                    
                    if order.product != 'chip-internacional-eua':
                        # Deletar eSIM para site                            
                        ApiStore.updateEsimStore(order_id)
            
                
            # Edit Voice
            if order.calls == True and VoiceCalls.objects.get(id_item=order_id).DoesNotExist:
                voice_d = VoiceCalls.objects.get(id_item=order_id)
                num_s = VoiceNumbers.objects.get(id=voice_d.id_number.id)
                
                num_s.number_status = 'DS'
                num_s.save()
                
                voice_d.delete()
        
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
        
        # Status sis : Status Loja
        status_sis_site = StatusStore.st_sis_site()
        # Só cancelar se todos os itens estiverem cancelados / reembolsados
        if (order_canc == 0 and ord_s == 'CC') or (order_reemb == 0 and ord_s == 'RB') or ord_s != 'DE':
            print('--------------------------- Alterar STATUS Loja')        
            if ord_s in status_sis_site:
                up_order_st_store(order.order_id,status_sis_site[ord_s])
        elif ord_s not in ['CC', 'RB', 'DE']:
            print('--------------------------- Alterar STATUS Loja')        
            up_order_st_store(order.order_id,status_sis_site[ord_s])        
                
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
            for st in ord_status:
                if order_st == st[0] :
                    addNote(f'Alterado de {st[1]} para {order.get_order_status_display()}')
            
        # Enviar email
        if ord_s == 'CN' and (type_sim == 'sim' or order_plan == 'USA'):
            send_email_sims.delay(id=order.id)


@shared_task
def up_order_st_store(order_id,order_st):
    time.sleep(0.5)
    apiStore = ApiStore.conectApiStore()
    update_store = {
            'status': order_st
        }
    apiStore.put(f'orders/{order_id}', update_store).json()


# @shared_task
# def update_st():
    
#     total_ord = 0
    
#     # Importar pedidos   
#     while True:
#         try:
#             ord = Orders.objects.filter(order_status="RE")
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
#                 id_order = id_sis.id
#                 order_status = id_sis.order_status
#                 status_sis_site = StatusStore.st_sis_site()
#                 if order_status in status_sis_site:                    
#                     up_order_st_store(id_sis, status_sis_site[order_status])
                
#                 total_ord += 1
#                 print(f'>>>>>>>>>> Pedidos {id_ord} = TOTAL {total_ord}')

#         n_page += 1

#     print(f'Total de pedidos processados: {total_ord}')
    
    
@shared_task
def update_st():
    # Importar pedidos
    apiStore = ApiStore.conectApiStore()
    
    # Definir números de páginas
    per_page = 100
    n_page = 1
    total_ord = 0
    
    while True:
        try:
            response = apiStore.get('orders', params={'order': 'desc', 'status': 'on-hold', 'per_page': per_page, 'page': n_page})
            response.raise_for_status()  # Verifica se a resposta HTTP contém um status de erro
            
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
            n_item = 1
            id_ord = order_store["id"]
            
            id_sis = Orders.objects.filter(order_id=id_ord).first()
            
            if id_sis != None:
                id_order = id_sis.id
                order_status = id_sis.order_status
                status_sis_site = StatusStore.st_sis_site()
                if order_status in status_sis_site:                    
                    up_order_st_store(id_sis, status_sis_site[order_status])
                
                total_ord += 1
                print(f'>>>>>>>>>> Pedidos {id_ord} = TOTAL {total_ord}')

        n_page += 1

    print(f'Total de pedidos processados: {total_ord}')
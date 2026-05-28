import random
from urllib.parse import urlparse
from celery import shared_task
import os
import http.client
import json
import time
from django.conf import settings

from .classes import ApiTC, ApiTI, ApiCM, operPlan, qrcodeChange
from apps.orders.models import Orders, Notes
from apps.orders.classes import ApiStore, StatusStore, NotesAdd, UpdateOrder, UpdateStore
from apps.send_email.tasks import send_email_sims
from apps.sims.models import Sims
from datetime import datetime, timedelta
import pytz
import requests
from django.core.exceptions import ObjectDoesNotExist
import logging
logger = logging.getLogger(__name__)

# Limite de processamento por execução (evita sobrecarga)
MAX_ORDERS_PER_RUN = 50

@shared_task(time_limit=300, soft_time_limit=240)
def sims_in_orders():
    """
    Atribui um SIM disponível a cada pedido com status ``AS`` (Atribuir SIM).

    Para cada pedido: determina a operadora pelo produto/tipo de SIM, seleciona
    o primeiro SIM disponível (``DS``) do inventário, associa ao pedido e atualiza
    o status para ``AA`` (Agd. Ativação). Sincroniza o ICCID na loja WooCommerce.
    Processa no máximo ``MAX_ORDERS_PER_RUN`` pedidos por execução.

    Limites: ``soft_time_limit=240s``, ``time_limit=300s``.
    """
    orders = Orders.objects.filter(order_status='AS')[:MAX_ORDERS_PER_RUN]
    total_count = Orders.objects.filter(order_status='AS').count()
    
    if total_count > MAX_ORDERS_PER_RUN:
        logger.warning(f'ATENÇÃO: {total_count} pedidos pendentes, processando apenas {MAX_ORDERS_PER_RUN} por vez')
        
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
        condition_i = ord.condition
        type_sim_i = ord.type_sim
        data_day_i = ord.data_day
        # celular_samsung = ord.celular_samsung
        reuso_sim = ord.ord_chip_nun
        update_store = {}
        
        # Se já houver SIM   
        if ord.id_sim != None:
            continue
        else:    
            # Notes
            def addNote(t_note):
                add_sim = Notes( 
                    id_item = Orders.objects.get(pk=id_id_i),
                    note = t_note,
                    type_note = 'S',
                )
                add_sim.save()

            if product_i == 'chip-internacional-eua-canada-e-mexico':
                if condition_i == 'novo-sim':
                    operator_i = 'TC'
                else:
                    operator_i = 'CM'
            elif product_i in operPlan.listPlan('TM'): # EUA Ilimitado
                operator_i = 'TM'
                sim_ds = Sims.objects.all().get(pk=0)
                addNote(f'eSIM EUA - SIM padrão adicionado')
            # elif product_i in operPlan.listPlan('AT') and type_sim_i == 'esim': # EUA Ilimitado
            #     operator_i = 'AT'
            elif product_i in operPlan.listPlan('TI'):
                operator_i = 'TI'
            elif product_i in operPlan.listPlan('TC'):
                operator_i = 'TC'
            elif product_i in operPlan.listPlan('OR'):
                operator_i = 'OR'
            else: operator_i = 'CM'
            
            # Select SIM
            if reuso_sim != '-':
                sim_ds = Sims.objects.filter(sim=reuso_sim).first()
            # elif operator_i == 'OR':
            #     sim_ds = Sims.objects.all().order_by('id').filter(operator=operator_i, type_sim=type_sim_i, sim_status='DS', data=data_day_i).first()
            #     if sim_ds:
            #         pass
            #     else:
            #         logger.info(f'-------------------- SIMs {operator_i} indisponíveis!')
            #         continue
            else:
                sim_ds = Sims.objects.all().order_by('id').filter(operator=operator_i, type_sim=type_sim_i, sim_status='DS').first()
                if sim_ds:
                    pass
                else:
                    logger.info(f'-------------------- SIMs {operator_i} indisponíveis!')
                    continue
            
            # update order
            # Save SIMs
            if (type_sim_i == 'esim' or reuso_sim != '-'):
                status_ord = 'AA'
                # Enviar e-mail
                send_email_sims.delay(id=id_id_i)
                addNote(f'Status alterado para Agd. Ativação')
                logger.info(f'Pedido {order_id_i} com eSIM ou reuso, status definido para AA e e-mail enviado!')
            elif type_sim_i == 'sim': status_ord = 'ES'
            
            order_put = Orders.objects.get(pk=id_id_i)
            order_put.id_sim_id = sim_ds.id            
            order_put.order_status = status_ord
            order_put.save()
            
            # update sim
            sim_put = Sims.objects.get(pk=sim_ds.id)
            sim_put.sim_status = 'AT'
            sim_put.save()
            _sim = sim_put.sim
            _qrcode = sim_put.link  # Usando o campo link que contém a URL do QR code

            addNote(f'(e)SIM {_sim} adicionado')

            # Atualizar pedido no site
            status_sis_site = StatusStore.st_sis_site()
            if status_ord in status_sis_site:
                update_store = {
                    'status': status_sis_site[status_ord]
                }
            
            # Gravar SIM e QRCode no site
            if ord.item_id_store:
                update_store['line_items'] = [
                    {
                        "id": int(ord.item_id_store),
                        "meta_data": [
                            {
                                "key": "_sim",
                                "value": _sim,
                            },
                            {
                                "key": "_qrcode",
                                "value": _qrcode if _qrcode else "",
                            }
                        ]
                    }
                ]
    
            apiStore = ApiStore.conectApiStore()
            apiStore.put(f'orders/{order_id_i}', update_store)
                             
            msg_info.append(f'Pedido {order_id_i} atualizados com sucesso')
            
            n_item_total += 1
    
        logger.info('>>>>>>>>>>>>>>>>>>>>>>> SIMs atribuidos!')
    

@shared_task(time_limit=110, soft_time_limit=100)
def simActivateTC(id=None):
    """
    Ativa SIMs da operadora **TelCom (TC)** para pedidos com status ``AA``.

    Args:
        id (int, optional): PK do pedido a ativar. Se ``None``, processa todos
            os pedidos com status ``AA``, operadora ``TC`` e data de ativação
            até amanhã.

    Fluxo: obtém token (cache Redis 540s) → busca endpointId pelo ICCID →
    troca de plano → ativa/reativa o SIM → atualiza status para ``AT`` →
    enfileira ``send_email_sims``.

    Limites: ``soft_time_limit=100s``, ``time_limit=110s``.
    """
    # dia anterior
    tz = pytz.timezone(settings.TIME_ZONE)
    today = datetime.now(tz).date()
    tomorrow = today +timedelta(days=1)

    logger.info('>>>>>>>>>> ATIVAÇÂO TC INICIADA')
    
    # Selecionar pedidos
    if id is None:
        orders_all = Orders.objects.filter(order_status='AA', id_sim__operator='TC', activation_date__lte=tomorrow)
    else:
        orders_all = Orders.objects.filter(pk=id)
    
    if orders_all.count() == 0:
        logger.info('>>>>>>>>>> ATIVAÇÂO TC FINALIZADA')
        return
            
    # Checar conexão com API
    def error_api():
        logger.error('>>>>>>>>>> ERRO API')
        # Checar Status
        UpdateOrder.upStatus(id_item,'EA')
        # Adicionar nota
        NotesAdd.addNote(order,f'ERRO API: {iccid} com erro na Telcon. Verificar erro.')
        error = 'error_apiResult'
        return error
    
    token_api = ApiTC.get_token()
    time.sleep(0.5)
    conn = http.client.HTTPSConnection(settings.APITC_HTTPCONN, timeout=10)
    headers = ApiTC.get_headers(token_api)
        
    for order in orders_all:
                        
        order = Orders.objects.get(pk=order.id)
        order_id = order.order_id
        logger.info(f'>>>>>>>>>>>>>>>>>>>>> Ativando {order_id}')
        id_item = order.id
        try:
            iccid = order.id_sim.sim
        except Exception:
            iccid = None
            continue
        dataDay = order.data_day
        product = order.product
        product_name = order.get_product_display()
        condition = order.condition
        
        # Variaveis globais        
        endpointId = None
        simStatus = None
        note = ''
        process = False
        token_api = None
        
        # Desativar Plano Anterior
        # if condition == 'reuso-sim' and product == 'chip-internacional-europa-1gb-total-05':
        #     # Encontrar ultimo pedido com o SIM de reuso
        #     last_order = Orders.objects.filter(id_sim=order.id_sim.sim).exclude(id=order.id).order_by('-activation_date').first()
        #     if last_order.order_status == 'AT':
        #         time.sleep(0.5)
        #         simDeactivateTC(last_order.id)
        
        # Verificar EndPointID / Status
        try:
            time.sleep(0.5)
            get_iccid = ApiTC.get_iccid(iccid, headers)
            endpointId = get_iccid[0]
            simStatus = get_iccid[1]
        except Exception:            
            error_api()
            continue
        ##
        
        # Alterar plano
        time.sleep(0.5)
        data_plan = ApiTC.planChange(endpointId,headers,dataDay, product)
        if data_plan == 0:
            UpdateOrder.upStatus(id_item,'EA')
            NotesAdd.addNote(order,f'{iccid} Plano não alterado. Verificar plano {dataDay} - TC: Plano não encontrado.')
            continue
        NotesAdd.addNote(order,f'{iccid} Plano alterado para {product_name} {dataDay} - TELCOM: {json.loads(data_plan)}')    

        if simStatus == 'Pre-Active':
            # Ativar SIM na operadora
            payload = json.dumps({
                "Request": {
                    "endPointId": f"{endpointId}"
                }
            })
            conn.request("POST", "/api/EndPointActivation", payload, headers)
            # Adicionar nota
            note = f'{iccid} ativado com sucesso na Telcon'
            
            process = True
            
        else:
            # Alterar SIM na operadora
            if simStatus == 'Active':
                logger.info('simStatus == Active')
                # Adicionar nota
                NotesAdd.addNote(order,f'{iccid} já estava ativado na Telcon')
                # Alterar Status
                UpdateOrder.upStatus(id_item,'AT')
                UpdateStore.upStore(
                    order_id = order_id,
                    item_id_store = order.item_id_store if order.item_id_store else None,
                    _status = 'AT',
                    status_g = 'AT',
                )               
                continue
            
            elif simStatus == 'Suspended':
                logger.info('simStatus == Suspended')
                payload = json.dumps({
                    "Request": {
                        "endPointId": f"{endpointId}",
                        "requestParam": {
                            "lifeCycle": "A",
                            "reason": "1"
                        }
                    }
                })
                time.sleep(0.5)
                conn.request("POST", "/api/EndPointLifeCycleChange", payload, headers)
                # Adicionar nota
                note = f'{iccid} reativado com sucesso na Telcon'
                
                process = True
                
            else:
                logger.info('simStatus == Other')
                # Alterar status
                UpdateOrder.upStatus(id_item,'EA')
                NotesAdd.addNote(order,f'{iccid} com erro de ativação na Telcon. Verificar erro.')
                continue
        
        if process == True:            
            
            time.sleep(0.5)            
            res = conn.getresponse()
            data = json.loads(res.read())
            resultCode = int(data["Response"]["resultCode"])
            resultDescription = data["Response"]["resultParam"]["resultDescription"]
            try:
                resultCode = int(data["Response"]["resultCode"])
                resultDescription = data["Response"]["resultParam"]["resultDescription"]
            except Exception:
                resultCode = None
                resultDescription = None
            
            if resultCode == 0:
                # Alterar status
                UpdateOrder.upStatus(id_item,'AT')
                UpdateStore.upStore(
                    order_id = order_id,
                    item_id_store = order.item_id_store if order.item_id_store else None,
                    _status = 'AT',
                    status_g = 'AT',
                )
                # Adicionar nota
                NotesAdd.addNote(order,f'{note} TC: {resultDescription}')
            else:
                # Alterar status
                UpdateOrder.upStatus(id_item,'EA')
                # Adicionar nota
                NotesAdd.addNote(order,f'TC: {resultDescription}')
        
        # Fecha a conexão
        conn.close()
                
    logger.info('>>>>>>>>>> ATIVAÇÂO TC FINALIZADA')


@shared_task(time_limit=110, soft_time_limit=100)
def simActivateTI(id=None):
    """
    Ativa SIMs da operadora **TelCom IMSI (TI)** para pedidos com status ``AA``.

    Funcionamento idêntico a :func:`simActivateTC`, porém usando credenciais
    e endpoints IMSI separados para planos com perfis IMSI específicos.

    Args:
        id (int, optional): PK do pedido a ativar. Se ``None``, processa em lote.

    Limites: ``soft_time_limit=100s``, ``time_limit=110s``.
    """
    tz = pytz.timezone(settings.TIME_ZONE)
    today = datetime.now(tz).date()
    tomorrow = today + timedelta(days=1)

    logger.info(f'>>>>>>>>>> ATIVAÇÂO TI INICIADA')
    
    # Selecionar pedidos
    if id is None:
        orders_all = Orders.objects.filter(order_status='AA', id_sim__operator='TI', activation_date__lte=tomorrow)
    else:
        orders_all = Orders.objects.filter(pk=id)
    
    if orders_all.count() == 0:
        logger.info('>>>>>>>>>> ATIVAÇÂO TI FINALIZADA')
        return
            
    # Checar conexão com API
    def error_api():
        logger.error('>>>>>>>>>> ERRO API')
        # Checar Status
        UpdateOrder.upStatus(id_item,'EA')
        # Adicionar nota
        NotesAdd.addNote(order,f'ERRO API: {iccid} com erro na Telcon. Verificar erro.')
        error = 'error_apiResult'
        return error
    
    token_api = ApiTI.get_token()
    time.sleep(0.5)
    conn = http.client.HTTPSConnection(settings.APITC_HTTPCONN, timeout=10)
    time.sleep(0.5)
    headers = ApiTI.get_headers(token_api)
        
    for order in orders_all:
                        
        order = Orders.objects.get(pk=order.id)
        order_id = order.order_id
        logger.info(f'>>>>>>>>>>>>>>>>>>>>> Ativando {order_id}')
        id_item = order.id
        try:
            iccid = order.id_sim.sim
        except Exception:
            iccid = None
            continue
        dataDay = order.data_day
        product = order.product
        product_name = order.get_product_display()
        
        # Variaveis globais        
        endpointId = None
        simStatus = None
        note = ''
        process = False
        token_api = None  
        
        # Verificar EndPointID / Status
        try:
            time.sleep(0.5)
            get_iccid = ApiTI.get_iccid(iccid, headers)
            endpointId = get_iccid[0]
            simStatus = get_iccid[1]
        except Exception:            
            error_api()
            continue
        ##
        
        # Alterar plano
        time.sleep(0.5)
        data_plan = ApiTI.planChange(endpointId,headers,dataDay, product)
        if data_plan == 0:
            UpdateOrder.upStatus(id_item,'EA')
            NotesAdd.addNote(order,f'{iccid} Plano não alterado. Verificar plano {dataDay} - TI: Plano não encontrado.')
            continue
        NotesAdd.addNote(order,f'{iccid} Plano alterado para {product_name} {dataDay}')    

        if simStatus == 'Pre-Active':
            # Ativar SIM na operadora
            payload = json.dumps({
                "Request": {
                    "endPointId": f"{endpointId}"
                }
            })
            time.sleep(0.5)
            conn.request("POST", "/api/EndPointActivation", payload, headers)
            # Adicionar nota
            note = f'{iccid} ativado com sucesso na Telcon'
            
            process = True
            
        else:
            # Alterar SIM na operadora
            if simStatus == 'Active':
                logger.info('simStatus == Active')
                # Adicionar nota
                NotesAdd.addNote(order,f'{iccid} já estava ativado na Telcon')
                # Alterar Status
                UpdateStore.upStore(
                    order_id = order_id,
                    item_id_store = order.item_id_store if order.item_id_store else None,
                    _status = 'AT',
                    status_g = 'AT',
                )             
                UpdateOrder.upStatus(id_item,'AT')
                continue
            
            elif simStatus == 'Suspended':
                logger.info('simStatus == Suspended')
                payload = json.dumps({
                    "Request": {
                        "endPointId": f"{endpointId}",
                        "requestParam": {
                            "lifeCycle": "A",
                            "reason": "1"
                        }
                    }
                })
                time.sleep(0.5)
                conn.request("POST", "/api/EndPointLifeCycleChange", payload, headers)
                # Adicionar nota
                note = f'{iccid} reativado com sucesso na Telcon'
                
                process = True
                
            else:
                logger.info('simStatus == Other')
                # Alterar status
                UpdateOrder.upStatus(id_item,'EA')
                NotesAdd.addNote(order,f'{iccid} com erro na ativação da Telcon. Verificar erro.')
                continue
        
        if process == True:            
            
            time.sleep(0.5)            
            res = conn.getresponse()
            data = json.loads(res.read())
            resultCode = int(data["Response"]["resultCode"])
            resultDescription = data["Response"]["resultParam"]["resultDescription"]
            try:
                resultCode = int(data["Response"]["resultCode"])
                resultDescription = data["Response"]["resultParam"]["resultDescription"]
            except Exception:
                resultCode = None
                resultDescription = None
            
            if resultCode == 0:
                # Alterar status
                UpdateOrder.upStatus(id_item,'AT')
                UpdateStore.upStore(
                    order_id = order_id,
                    item_id_store = order.item_id_store if order.item_id_store else None,
                    _status = 'AT',
                    status_g = 'AT',
                )            
                # Adicionar nota
                NotesAdd.addNote(order,f'{note} TI: {resultDescription}')
            else:
                # Alterar status
                # UpdateOrder.upStatus(id_item,'EA')
                # Adicionar nota
                NotesAdd.addNote(order,f'TI: {resultDescription}')
        
        # Fecha a conexão
        conn.close()

    logger.info('>>>>>>>>>> ATIVAÇÂO TI FINALIZADA')


@shared_task(time_limit=300, soft_time_limit=270)
def simDeactivateTC(id=None):
    """
    Desativa SIMs das operadoras **TelCom (TC)** e **TelCom IMSI (TI)** com plano expirado.

    Executada diariamente às 00:00. Seleciona pedidos com status ``AT`` e
    data de ativação vencida (activation_date + days <= ontem).

    Args:
        id (int, optional): PK do pedido a desativar. Se ``None``, processa em lote.

    Limites: ``soft_time_limit=270s``, ``time_limit=300s``.
    """
    logger.info('>>>>>>>>>> DESATIVAÇÃO TC INICIADA')
    
    timezone = pytz.timezone(settings.TIME_ZONE)

    now = datetime.now(timezone)
    yesterday = now.date() - timedelta(days=1)

    # Selecionar pedidos
    if id is None:       
        orders_to_process = Orders.objects.filter(order_status='AT', id_sim__operator__in=['TC', 'TI']).order_by('-id')
    else:
        orders_to_process = Orders.objects.filter(pk=id)

    if not orders_to_process.exists():
        logger.info('>>>>>>>>>> DESATIVAÇÃO TC FINALIZADA <<<<<<<<<<')
        return
    
    def error_api(order_item, iccid_val):
        logger.error(f'>>>>>>>>>> ERRO API PARA O PEDIDO {order_item.order_id} <<<<<<<<<<')
        UpdateOrder.upStatus(order_item.id, 'ED')
        NotesAdd.addNote(order_item, f'ERRO API: {iccid_val} com erro na Telcon. Verificar erro.')

    for order in orders_to_process:
        # Garante que activation_date e days não são nulos
        if order.activation_date is None or order.days is None:
            continue

        # Calcula a data de desativação
        # A lógica é: data de ativação + (duração do plano - 1 dia)
        deactivation_date = order.activation_date + timedelta(days=order.days - 1)

        # Se um ID específico não foi passado, só desativa se a data for ontem ou anterior
        if id is None and deactivation_date > yesterday:
            continue

        try:
            iccid = order.id_sim.sim
        except (AttributeError, ObjectDoesNotExist):
            logger.error(f"Pedido {order.order_id} sem SIM associado.")
            UpdateOrder.upStatus(order.id, 'DE')
            UpdateStore.upStore(
                order_id=order.order_id,
                item_id_store=order.item_id_store if order.item_id_store else None,
                _status='DE',
                status_g='DE',
            )
            continue

        try:
            # Gerar token de acesso a API
            time.sleep(0.5)
            token_api = ApiTC.get_token()
            conn = http.client.HTTPSConnection(settings.APITC_HTTPCONN, timeout=10)
            headers = ApiTC.get_headers(token_api, cookie=True)
            
            get_iccid_result = ApiTC.get_iccid(iccid, headers)
            endpointId = get_iccid_result[0]

            payload = json.dumps({
                "Request": {
                    "endPointId": f"{endpointId}",
                    "requestParam": {
                        "lifeCycle": "S",
                        "reason": "1"
                    }
                }
            })
            
            time.sleep(0.5)
            conn.request("POST", "/api/EndPointLifeCycleChange", payload, headers)
            
            res = conn.getresponse()
            data = json.loads(res.read())
            
            resultCode = int(data.get("Response", {}).get("resultCode", -1))
            resultDescription = data.get("Response", {}).get("resultParam", {}).get("resultDescription", str(data))

            if resultCode == 0:
                logger.info(f'Pedido {order.order_id} desativado com sucesso.')
                if id is None:
                    UpdateOrder.upStatus(order.id, 'DE')
                    UpdateStore.upStore(
                        order_id=order.order_id,
                        item_id_store=order.item_id_store if order.item_id_store else None,
                        _status='DE',
                        status_g='DE',
                    )
                    sim_put = Sims.objects.get(pk=order.id_sim.id)
                    sim_put.sim_status = 'DE'
                    sim_put.save()
                NotesAdd.addNote(order, f'{iccid} desativado com sucesso na Telcon. TC: {resultDescription}')
            else:
                logger.error(f'Erro ao desativar pedido {order.order_id}.')
                if id is None:
                    UpdateOrder.upStatus(order.id, 'ED')
                NotesAdd.addNote(order, f'ERRO DESATIVADO: {iccid} com erro na Telcon. TC: {resultDescription}')

        except Exception as e:
            logger.error(f"Erro inesperado ao processar desativação do pedido {order.order_id}: {e}", exc_info=True)
            error_api(order, iccid if 'iccid' in locals() else 'N/A')
        
        finally:
            if 'conn' in locals() and conn:
                conn.close()
                
    logger.info('>>>>>>>>>> DESATIVAÇÃO TC FINALIZADA <<<<<<<<<<')


@shared_task(time_limit=300, soft_time_limit=270)
def simDeactivateAll(id=None):
    """
    Desativa SIMs de **todas as operadoras exceto TC/TI** com plano expirado.

    Executada diariamente às 00:00. Seleciona pedidos com status ``AT`` de
    operadoras como TM, CM, MS, OR e AT.

    Args:
        id (int, optional): PK do pedido a desativar. Se ``None``, processa em lote.

    Limites: ``soft_time_limit=270s``, ``time_limit=300s``.
    """
    logger.info('>>>>>>>>>> DESATIVAÇÃO ALL INICIADA')
    
    timezone = pytz.timezone(settings.TIME_ZONE)
    now = datetime.now(timezone)
    yesterday = now.date() - timedelta(days=1)

    # Selecionar pedidos
    if id is None:       
        orders_to_process = Orders.objects.filter(order_status='AT').exclude(id_sim__operator__in=['TC', 'TI']).order_by('-id')
    else:
        orders_to_process = Orders.objects.filter(pk=id)

    if not orders_to_process.exists():
        logger.info('>>>>>>>>>> DESATIVAÇÃO ALL FINALIZADA <<<<<<<<<<')
        return
    
    for order in orders_to_process:
        # Garante que activation_date e days não são nulos
        if order.activation_date is None or order.days is None:
            continue

        # Calcula a data de desativação
        # A lógica é: data de ativação + (duração do plano - 1 dia)
        deactivation_date = order.activation_date + timedelta(days=order.days - 1)

        # Se um ID específico não foi passado, só desativa se a data for ontem ou anterior
        if id is None and deactivation_date > yesterday:
            continue

        if id is None:
            UpdateOrder.upStatus(order.id, 'DE')
            UpdateStore.upStore(
                order_id=order.order_id,
                item_id_store=order.item_id_store if order.item_id_store else None,
                _status='DE',
                status_g='DE',
            )
            if order.id_sim:
                sim_put = Sims.objects.get(pk=order.id_sim.id)
                sim_put.sim_status = 'DE'
                sim_put.save()
        NotesAdd.addNote(order, f'Desativado com sucesso. Processo automático')
        
    logger.info(f'Pedido {order.order_id} desativado com sucesso.')                
    logger.info('>>>>>>>>>> DESATIVAÇÃO ALL FINALIZADA <<<<<<<<<<')


@shared_task(time_limit=110, soft_time_limit=100)
def simActivateTM(id=None):
    """
    Ativa SIMs da operadora **T-Mobile (TM)** para pedidos com status ``AA``.

    Args:
        id (int, optional): PK do pedido a ativar. Se ``None``, processa todos
            os pedidos com status ``AA`` e operadora ``TM``.

    Limites: ``soft_time_limit=100s``, ``time_limit=110s``.
    """
    tz = pytz.timezone(settings.TIME_ZONE)
    today = datetime.now(tz).date()
    tomorrow = today + timedelta(days=1)
    
    logger.info('>>>>>>>>>> ATIVAÇÂO TM INICIADA')
    
    # Selecionar pedidos
    if id is None:
        orders_all = Orders.objects.filter(order_status='AA', id_sim__operator='TM')
    else:
        orders_all = Orders.objects.filter(pk=id)
    
    if orders_all.count() == 0:
        logger.info('>>>>>>>>>> ATIVAÇÂO TM FINALIZADA')
        return
    
    # Selecionar pedidos
    if id is None:
        orders_all = Orders.objects.filter(order_status='AA', id_sim__operator='TM', activation_date__lte=tomorrow)
    else:
        orders_all = Orders.objects.filter(pk=id)        
    
    for order in orders_all:
        
        order = Orders.objects.get(pk=order.id)
        order_id = order.order_id
        id_item = order.id
        if order.id_sim.type_sim == 'sim':
            iccid = order.id_sim.sim
            imei = ""
        else:
            iccid = order.cell_eid
            imei = order.cell_imei
        activation_date = order.activation_date
        days = order.days
        if days < 7:
            days = 7
        else:
            days = order.days
                
        # Dados para a solicitação
        url = f"{settings.APITM_URL.rstrip('/')}/api/public/orders"
        payload = json.dumps({
            "planName": "$50",
            "carrier": "T-Mobile",
            "day": int(days),
            "sim": iccid,
            "imei": imei,
            "activationDate": activation_date.strftime("%Y-%m-%d"),
            "areaCode": "",
            "customerEmail": "",
            "comment": "",
        })        
        
        # Cabeçalhos da solicitação
        headers = {
            'Content-Type': 'application/json',
            "Authorization": f"Bearer {settings.APITM_TOKEN}"
        }

        try:
            response = requests.post(url, data=payload, headers=headers, timeout=30, allow_redirects=False)
        except requests.exceptions.RequestException as e:
            UpdateOrder.upStatus(id_item,'EA')
            NotesAdd.addNote(order, f'Erro de comunicação com API T-Mobile para SIM {iccid}: {e}')
            continue

        # A API TM pode redirecionar para /login quando URL/token estão inválidos.
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get('Location', 'N/A')
            UpdateOrder.upStatus(id_item,'EA')
            NotesAdd.addNote(
                order,
                f'Redirecionamento inesperado na API T-Mobile para SIM {iccid}. '
                f'Status HTTP: {response.status_code}. Location: {location}. '
                'Verificar APITM_URL/APITM_TOKEN.'
            )
            continue

        if response.status_code in (401, 403):
            UpdateOrder.upStatus(id_item,'EA')
            NotesAdd.addNote(
                order,
                f'Falha de autenticação na API T-Mobile para SIM {iccid}. '
                f'Status HTTP: {response.status_code}. Verificar APITM_TOKEN.'
            )
            continue

        data = response.content
        # Decodifica a resposta
        try:
            response_data = json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, ValueError) as e:
            # API retornou resposta vazia ou inválida
            UpdateOrder.upStatus(id_item,'EA')
            NotesAdd.addNote(
                order,
                f'Erro ao decodificar resposta da API para SIM {iccid}. '
            )
            continue
        
        # API antiga: {'code': 0} | API nova: {'success': True, 'order': {...}}
        success_by_code = ('code' in response_data and response_data.get('code') == 0)
        success_by_flag = (response_data.get('success') is True and isinstance(response_data.get('order'), dict))

        if success_by_code or success_by_flag:
            # Alterar status
            UpdateOrder.upStatus(id_item,'AT')
            UpdateStore.upStore(
                order_id = order_id,
                item_id_store = order.item_id_store if order.item_id_store else None,
                _status = 'AT',
                status_g = 'AT',
            )
            # Adicionar nota
            tm_order_status = response_data.get('order', {}).get('status') if isinstance(response_data.get('order'), dict) else None
            if tm_order_status:
                NotesAdd.addNote(order,f'{iccid} Enviado para ativação na T-Mobile. Status operadora: {tm_order_status}')
            else:
                NotesAdd.addNote(order,f'{iccid} Enviado para ativação na T-Mobile')
        else:
            # Alterar status
            UpdateOrder.upStatus(id_item,'EA')
            # Adicionar nota
            if 'error' in response_data:
                NotesAdd.addNote(order,f'Erro retornado pela API ao ativar o SIM {iccid}. Verificar manualmente. {response_data.get("error")}')
            else:
                NotesAdd.addNote(order,f'Código não identificado ao ativar o SIM {iccid}. Verificar manualmente. {response_data}')

                
    logger.info('>>>>>>>>>> ATIVAÇÂO TM FINALIZADA')


@shared_task(time_limit=110, soft_time_limit=100)
def simActivateCM(id=None):
    """
    Ativa SIMs da operadora **China Mobile (CM)** para pedidos com status ``AA``.

    Usa autenticação por assinatura HMAC-SHA256 (chave/secret) armazenada
    nas configurações do Django.

    Args:
        id (int, optional): PK do pedido a ativar. Se ``None``, processa em lote.

    Limites: ``soft_time_limit=100s``, ``time_limit=110s``.
    """
    import base64
    import hashlib
    import json
    import http.client
    from urllib.parse import urlparse
    import time 

    list_cm_europe = [
        ["5", "500mb-dia", "D2206291850234693769"],
        ["5", "1gb", "D2206291850234693769"],
        ["5", "2gb", "D2206291855407008527"],
        ["6", "500mb-dia", "D2206091135171925874"],
        ["6", "1gb", "D2206091135171925874"],
        ["6", "2gb", "D2206291856141314480"],
        ["7", "500mb-dia", "D2206091135171925874"],
        ["7", "1gb", "D2206091135171925874"],
        ["7", "2gb", "D2206291856141314480"],
        ["8", "500mb-dia", "D2206091135414428250"],
        ["8", "1gb", "D2206091135414428250"],
        ["8", "2gb", "D2206291857110154857"],
        ["9", "500mb-dia", "D2206091135414428250"],
        ["9", "1gb", "D2206091135414428250"],
        ["9", "2gb", "D2206291857110154857"],
        ["10", "500mb-dia", "D2206091135414428250"],
        ["10", "1gb", "D2206091135414428250"],
        ["10", "2gb", "D2206291857110154857"],
        ["11", "500mb-dia", "D2206091136019095391"],
        ["11", "1gb", "D2206091136019095391"],
        ["11", "2gb", "D2206291857403368188"],
        ["12", "500mb-dia", "D2206091136019095391"],
        ["12", "1gb", "D2206091136019095391"],
        ["12", "2gb", "D2206291857403368188"],
        ["13", "500mb-dia", "D2206091136019095391"],
        ["13", "1gb", "D2206091136019095391"],
        ["13", "2gb", "D2206291857403368188"],
        ["14", "500mb-dia", "D2206091136019095391"],
        ["14", "1gb", "D2206091136019095391"],
        ["14", "2gb", "D2206291857403368188"],
        ["15", "500mb-dia", "D2206091136019095391"],
        ["15", "1gb", "D2206091136019095391"],
        ["15", "2gb", "D2206291857403368188"],
        ["16", "500mb-dia", "D2206291851030076782"],
        ["16", "1gb", "D2206291851030076782"],
        ["16", "2gb", "D2206291858199844782"],
        ["17", "500mb-dia", "D2206291851030076782"],
        ["17", "1gb", "D2206291851030076782"],
        ["17", "2gb", "D2206291858199844782"],
        ["18", "500mb-dia", "D2206291851030076782"],
        ["18", "1gb", "D2206291851030076782"],
        ["18", "2gb", "D2206291858199844782"],
        ["19", "500mb-dia", "D2206291851030076782"],
        ["19", "1gb", "D2206291851030076782"],
        ["19", "2gb", "D2206291858199844782"],
        ["20", "500mb-dia", "D2206291851030076782"],
        ["20", "1gb", "D2206291851030076782"],
        ["20", "2gb", "D2206291858199844782"],
        ["21", "500mb-dia", "D2206091136223123003"],
        ["21", "1gb", "D2206091136223123003"],
        ["21", "2gb", "D2206291858438338083"],
        ["22", "500mb-dia", "D2206091136223123003"],
        ["22", "1gb", "D2206091136223123003"],
        ["22", "2gb", "D2206291858438338083"],
        ["23", "500mb-dia", "D2206091136223123003"],
        ["23", "1gb", "D2206091136223123003"],
        ["23", "2gb", "D2206291858438338083"],
        ["24", "500mb-dia", "D2206091136223123003"],
        ["24", "1gb", "D2206091136223123003"],
        ["24", "2gb", "D2206291858438338083"],
        ["25", "500mb-dia", "D2206091136223123003"],
        ["25", "1gb", "D2206091136223123003"],
        ["25", "2gb", "D2206291858438338083"],
        ["26", "500mb-dia", "D2206091136223123003"],
        ["26", "1gb", "D2206091136223123003"],
        ["26", "2gb", "D2206291858438338083"],
        ["27", "500mb-dia", "D2206091136223123003"],
        ["27", "1gb", "D2206091136223123003"],
        ["27", "2gb", "D2206291858438338083"],
        ["28", "500mb-dia", "D2206091136223123003"],
        ["28", "1gb", "D2206091136223123003"],
        ["28", "2gb", "D2206291858438338083"],
        ["29", "500mb-dia", "D2206091136223123003"],
        ["29", "1gb", "D2206091136223123003"],
        ["29", "2gb", "D2206291858438338083"],
        ["30", "500mb-dia", "D2206091136223123003"],
        ["30", "1gb", "D2206091136223123003"],
        ["30", "2gb", "D2206291858438338083"],
    ]

    list_cm_global_ch = [
        ["5", "500mb-dia", "D181031181258_229560"],
        ["5", "1gb", "D2206301156230194956"],
        ["5", "2gb", "D2206301205165738953"],
        ["6", "500mb-dia", "D181031181914_229650"],
        ["6", "1gb", "D2206091105276234237"],
        ["6", "2gb", "D2206301205486118193"],
        ["7", "500mb-dia", "D181031181914_229650"],
        ["7", "1gb", "D2206091105276234237"],
        ["7", "2gb", "D2206301205486118193"],
        ["8", "500mb-dia", "D181031182542_229740"],
        ["8", "1gb", "D2206091107307032864"],
        ["8", "2gb", "D2206301206197251946"],
        ["9", "500mb-dia", "D181031182542_229740"],
        ["9", "1gb", "D2206091107307032864"],
        ["9", "2gb", "D2206301206197251946"],
        ["10", "500mb-dia", "D181031182542_229740"],
        ["10", "1gb", "D2206091107307032864"],
        ["10", "2gb", "D2206301206197251946"],
        ["11", "500mb-dia", "D181031183135_229830"],
        ["11", "1gb", "D2206091108433606607"],
        ["11", "2gb", "D2206301206528368501"],
        ["12", "500mb-dia", "D181031183135_229830"],
        ["12", "1gb", "D2206091108433606607"],
        ["12", "2gb", "D2206301206528368501"],
        ["13", "500mb-dia", "D181031183135_229830"],
        ["13", "1gb", "D2206091108433606607"],
        ["13", "2gb", "D2206301206528368501"],
        ["14", "500mb-dia", "D181031183135_229830"],
        ["14", "1gb", "D2206091108433606607"],
        ["14", "2gb", "D2206301206528368501"],
        ["15", "500mb-dia", "D181031183135_229830"],
        ["15", "1gb", "D2206091108433606607"],
        ["15", "2gb", "D2206301206528368501"],
        ["16", "500mb-dia", "D210521035722_568094"],
        ["16", "1gb", "D2206301157034705599"],
        ["16", "2gb", "D2206301207302789206"],
        ["17", "500mb-dia", "D210521035722_568094"],
        ["17", "1gb", "D2206301157034705599"],
        ["17", "2gb", "D2206301207302789206"],
        ["18", "500mb-dia", "D210521035722_568094"],
        ["18", "1gb", "D2206301157034705599"],
        ["18", "2gb", "D2206301207302789206"],
        ["19", "500mb-dia", "D210521035722_568094"],
        ["19", "1gb", "D2206301157034705599"],
        ["19", "2gb", "D2206301207302789206"],
        ["20", "500mb-dia", "D210521035722_568094"],
        ["20", "1gb", "D2206301157034705599"],
        ["20", "2gb", "D2206301207302789206"],
        ["21", "500mb-dia", "D210521075722_568297"],
        ["21", "1gb", "D2206301157335495089"],
        ["21", "2gb", "D2206301207564086363"], 
        ["22", "500mb-dia", "D210521075722_568297"],
        ["22", "1gb", "D2206301157335495089"],
        ["22", "2gb", "D2206301207564086363"], 
        ["23", "500mb-dia", "D210521075722_568297"],
        ["23", "1gb", "D2206301157335495089"],
        ["23", "2gb", "D2206301207564086363"], 
        ["24", "500mb-dia", "D210521075722_568297"],
        ["24", "1gb", "D2206301157335495089"],
        ["24", "2gb", "D2206301207564086363"], 
        ["25", "500mb-dia", "D210521075722_568297"],
        ["25", "1gb", "D2206301157335495089"],
        ["25", "2gb", "D2206301207564086363"], 
        ["26", "500mb-dia", "D181031183714_229920"],
        ["26", "1gb", "D2206091109242038213"],
        ["26", "2gb", "D2206301208289772531"],  
        ["27", "500mb-dia", "D181031183714_229920"],
        ["27", "1gb", "D2206091109242038213"],
        ["27", "2gb", "D2206301208289772531"],  
        ["28", "500mb-dia", "D181031183714_229920"],
        ["28", "1gb", "D2206091109242038213"],
        ["28", "2gb", "D2206301208289772531"],  
        ["29", "500mb-dia", "D181031183714_229920"],
        ["29", "1gb", "D2206091109242038213"],
        ["29", "2gb", "D2206301208289772531"],
        ["30", "500mb-dia", "D181031183714_229920"],
        ["30", "1gb", "D2206091109242038213"],
        ["30", "2gb", "D2206301208289772531"],
    ]
    
    list_cm_global = [
        ["5", "500mb-dia", "D181030042539_227624"],
        ["5", "1gb", "D2205171902194598628"],
        ["5", "2gb", "D2206301059342263262"],
        ["6", "500mb-dia", "D181030043319_227719"],
        ["6", "1gb", "D2205171902519779100"],
        ["6", "2gb", "D2206301100122278918"],
        ["7", "500mb-dia", "D181030043319_227719"],
        ["7", "1gb", "D2205171902519779100"],
        ["7", "2gb", "D2206301100122278918"],
        ["8", "500mb-dia", "D181030044052_227812"],
        ["8", "1gb", "D2205171903285254520"],
        ["8", "2gb", "D2206301100537072952"],
        ["9", "500mb-dia", "D181030044052_227812"],
        ["9", "1gb", "D2205171903285254520"],
        ["9", "2gb", "D2206301100537072952"],
        ["10", "500mb-dia", "D181030044052_227812"],
        ["10", "1gb", "D2205171903285254520"],
        ["10", "2gb", "D2206301100537072952"],
        ["11", "500mb-dia", "D181030060952_227953"],
        ["11", "1gb", "D2205171904079201878"],
        ["11", "2gb", "D2206301101255910272"],
        ["12", "500mb-dia", "D181030060952_227953"],
        ["12", "1gb", "D2205171904079201878"],
        ["12", "2gb", "D2206301101255910272"],
        ["13", "500mb-dia", "D181030060952_227953"],
        ["13", "1gb", "D2205171904079201878"],
        ["13", "2gb", "D2206301101255910272"],
        ["14", "500mb-dia", "D181030060952_227953"],
        ["14", "1gb", "D2205171904079201878"],
        ["14", "2gb", "D2206301101255910272"],
        ["15", "500mb-dia", "D181030060952_227953"],
        ["15", "1gb", "D2205171904079201878"],
        ["15", "2gb", "D2206301101255910272"],
        ["16", "500mb-dia", "D210520111201_567505"],
        ["16", "1gb", "D2205171904426262385"],
        ["16", "2gb", "D2206301102116254489"],
        ["17", "500mb-dia", "D210520111201_567505"],
        ["17", "1gb", "D2205171904426262385"],
        ["17", "2gb", "D2206301102116254489"],
        ["18", "500mb-dia", "D210520111201_567505"],
        ["18", "1gb", "D2205171904426262385"],
        ["18", "2gb", "D2206301102116254489"],
        ["19", "500mb-dia", "D210520111201_567505"],
        ["19", "1gb", "D2205171904426262385"],
        ["19", "2gb", "D2206301102116254489"],
        ["20", "500mb-dia", "D210520111201_567505"],
        ["20", "1gb", "D2205171904426262385"],
        ["20", "2gb", "D2206301102116254489"],
        ["21", "500mb-dia", "D210521020847_567890"],
        ["21", "1gb", "D2205171905123822954"],
        ["21", "2gb", "D2206301102507299017"], 
        ["22", "500mb-dia", "D210521020847_567890"],
        ["22", "1gb", "D2205171905123822954"],
        ["22", "2gb", "D2206301102507299017"], 
        ["23", "500mb-dia", "D210521020847_567890"],
        ["23", "1gb", "D2205171905123822954"],
        ["23", "2gb", "D2206301102507299017"], 
        ["24", "500mb-dia", "D210521020847_567890"],
        ["24", "1gb", "D2205171905123822954"],
        ["24", "2gb", "D2206301102507299017"], 
        ["25", "500mb-dia", "D210521020847_567890"],
        ["25", "1gb", "D2205171905123822954"],
        ["25", "2gb", "D2206301102507299017"], 
        ["26", "500mb-dia", "D181030062003_228049"],
        ["26", "1gb", "D2205171905428070570"],
        ["26", "2gb", "D2206301103268430586"],  
        ["27", "500mb-dia", "D181030062003_228049"],
        ["27", "1gb", "D2205171905428070570"],
        ["27", "2gb", "D2206301103268430586"],  
        ["28", "500mb-dia", "D181030062003_228049"],
        ["28", "1gb", "D2205171905428070570"],
        ["28", "2gb", "D2206301103268430586"],  
        ["29", "500mb-dia", "D181030062003_228049"],
        ["29", "1gb", "D2205171905428070570"],
        ["29", "2gb", "D2206301103268430586"],
        ["30", "500mb-dia", "D181030062003_228049"],
        ["30", "1gb", "D2205171905428070570"],
        ["30", "2gb", "D2206301103268430586"],
    ]
    
    list_cm_north = [
        ["5", "500mb-dia", "D181029074947_215300"],
        ["5", "1gb", "D2206091118158677818"],
        ["5", "2gb", "D2206291909256195940"],
        ["6", "500mb-dia", "D181029074947_215300"],
        ["6", "1gb", "D2206091118158677818"],
        ["6", "2gb", "D2206291909256195940"],
        ["7", "500mb-dia", "D181029074947_215300"],
        ["7", "1gb", "D2206091118158677818"],
        ["7", "2gb", "D2206291909256195940"],
        ["8", "500mb-dia", "D181029075127_215305"],
        ["8", "1gb", "D2206091118433144508"],
        ["8", "2gb", "D2206291910012200492"],
        ["9", "500mb-dia", "D181029075127_215305"],
        ["9", "1gb", "D2206091118433144508"],
        ["9", "2gb", "D2206291910012200492"],
        ["10", "500mb-dia", "D181029075127_215305"],
        ["10", "1gb", "D2206091118433144508"],
        ["10", "2gb", "D2206291910012200492"],
        ["11", "500mb-dia", "D181029075231_215312"],
        ["11", "1gb", "D2206291906432072367"],
        ["11", "2gb", "D2206291910234719163"],
        ["12", "500mb-dia", "D181029075231_215312"],
        ["12", "1gb", "D2206291906432072367"],
        ["12", "2gb", "D2206291910234719163"],
        ["13", "500mb-dia", "D181029075347_215318"],
        ["13", "1gb", "D2206091119091070123"],
        ["13", "2gb", "D2206291910482445815"],
        ["14", "500mb-dia", "D181029075347_215318"],
        ["14", "1gb", "D2206091119091070123"],
        ["14", "2gb", "D2206291910482445815"],
        ["15", "500mb-dia", "D181029075347_215318"],
        ["15", "1gb", "D2206091119091070123"],
        ["15", "2gb", "D2206291910482445815"],
        ["16", "500mb-dia", "D181029075545_215323"],
        ["16", "1gb", "D2206291907323030471"],
        ["16", "2gb", "D2206291911183379323"],
        ["17", "500mb-dia", "D181029075545_215323"],
        ["17", "1gb", "D2206291907323030471"],
        ["17", "2gb", "D2206291911183379323"],
        ["18", "500mb-dia", "D181029075545_215323"],
        ["18", "1gb", "D2206291907323030471"],
        ["18", "2gb", "D2206291911183379323"],
        ["19", "500mb-dia", "D181029075545_215323"],
        ["19", "1gb", "D2206291907323030471"],
        ["19", "2gb", "D2206291911183379323"],
        ["20", "500mb-dia", "D181029075545_215323"],
        ["20", "1gb", "D2206291907323030471"],
        ["20", "2gb", "D2206291911183379323"],
        ["21", "500mb-dia", "D181029075646_215328"],
        ["21", "1gb", "D2206091119350589636"],
        ["21", "2gb", "D2206291911447523252"],
        ["22", "500mb-dia", "D181029075646_215328"],
        ["22", "1gb", "D2206091119350589636"],
        ["22", "2gb", "D2206291911447523252"],
        ["23", "500mb-dia", "D181029075646_215328"],
        ["23", "1gb", "D2206091119350589636"],
        ["23", "2gb", "D2206291911447523252"],
        ["24", "500mb-dia", "D181029075646_215328"],
        ["24", "1gb", "D2206091119350589636"],
        ["24", "2gb", "D2206291911447523252"],
        ["25", "500mb-dia", "D181029075646_215328"],
        ["25", "1gb", "D2206091119350589636"],
        ["25", "2gb", "D2206291911447523252"],
        ["26", "500mb-dia", "D181029075646_215328"],
        ["26", "1gb", "D2206091119350589636"],
        ["26", "2gb", "D2206291911447523252"],
        ["27", "500mb-dia", "D181029075646_215328"],
        ["27", "1gb", "D2206091119350589636"],
        ["27", "2gb", "D2206291911447523252"],
        ["28", "500mb-dia", "D181029075646_215328"],
        ["28", "1gb", "D2206091119350589636"],
        ["28", "2gb", "D2206291911447523252"],
        ["29", "500mb-dia", "D181029075646_215328"],
        ["29", "1gb", "D2206091119350589636"],
        ["29", "2gb", "D2206291911447523252"],
        ["30", "500mb-dia", "D181029075646_215328"],
        ["30", "1gb", "D2206091119350589636"],
        ["30", "2gb", "D2206291911447523252"],        
    ]
    
    list_cm_south = [
        ["5", "500mb-dia", "D2404031210062193114"],
        ["5", "1gb", "D2404031212486801615"],
        ["5", "2gb", "D2404031214315532898"],
        ["6", "500mb-dia", "D2404031210226737497"],
        ["6", "1gb", "D2404031213010518789"],
        ["6", "2gb", "D2404031214448357348"],
        ["7", "500mb-dia", "D2404031210226737497"],
        ["7", "1gb", "D2404031213010518789"],
        ["7", "2gb", "D2404031214448357348"],
        ["8", "500mb-dia", "D2404031210358569469"],
        ["8", "1gb", "D2404031213148743416"],
        ["8", "2gb", "D2404031214563569617"],
        ["9", "500mb-dia", "D2404031210358569469"],
        ["9", "1gb", "D2404031213148743416"],
        ["9", "2gb", "D2404031214563569617"],
        ["10", "500mb-dia", "D2404031210358569469"],
        ["10", "1gb", "D2404031213148743416"],
        ["10", "2gb", "D2404031214563569617"],
        ["11", "500mb-dia", "D2404031210506288539"],
        ["11", "1gb", "D2404031213254297691"],
        ["11", "2gb", "D2404031215086886884"],
        ["12", "500mb-dia", "D2404031210506288539"],
        ["12", "1gb", "D2404031213254297691"],
        ["12", "2gb", "D2404031215086886884"],
        ["13", "500mb-dia", "D2404031210506288539"],
        ["13", "1gb", "D2404031213254297691"],
        ["13", "2gb", "D2404031215086886884"],
        ["14", "500mb-dia", "D2404031210506288539"],
        ["14", "1gb", "D2404031213254297691"],
        ["14", "2gb", "D2404031215086886884"],
        ["15", "500mb-dia", "D2404031210506288539"],
        ["15", "1gb", "D2404031213254297691"],
        ["15", "2gb", "D2404031215086886884"],
        ["16", "500mb-dia", "D2404031211046731495"],
        ["16", "1gb", "D2404031213365262561"],
        ["16", "2gb", "D2404031215208679205"],
        ["17", "500mb-dia", "D2404031211046731495"],
        ["17", "1gb", "D2404031213365262561"],
        ["17", "2gb", "D2404031215208679205"],
        ["18", "500mb-dia", "D2404031211046731495"],
        ["18", "1gb", "D2404031213365262561"],
        ["18", "2gb", "D2404031215208679205"],
        ["19", "500mb-dia", "D2404031211046731495"],
        ["19", "1gb", "D2404031213365262561"],
        ["19", "2gb", "D2404031215208679205"],
        ["20", "500mb-dia", "D2404031211046731495"],
        ["20", "1gb", "D2404031213365262561"],
        ["20", "2gb", "D2404031215208679205"],
        ["21", "500mb-dia", "D2404031211172035310"],
        ["21", "1gb", "D2404031213486570202"],
        ["21", "2gb", "D2404031215315038594"],
        ["22", "500mb-dia", "D2404031211172035310"],
        ["22", "1gb", "D2404031213486570202"],
        ["22", "2gb", "D2404031215315038594"],
        ["23", "500mb-dia", "D2404031211172035310"],
        ["23", "1gb", "D2404031213486570202"],
        ["23", "2gb", "D2404031215315038594"],
        ["24", "500mb-dia", "D2404031211172035310"],
        ["24", "1gb", "D2404031213486570202"],
        ["24", "2gb", "D2404031215315038594"],
        ["25", "500mb-dia", "D2404031211172035310"],
        ["25", "1gb", "D2404031213486570202"],
        ["25", "2gb", "D2404031215315038594"],
        ["26", "500mb-dia", "D2404031211172035310"],
        ["26", "1gb", "D2404031213486570202"],
        ["26", "2gb", "D2404031215315038594"],
        ["27", "500mb-dia", "D2404031211172035310"],
        ["27", "1gb", "D2404031213486570202"],
        ["27", "2gb", "D2404031215315038594"],
        ["28", "500mb-dia", "D2404031211172035310"],
        ["28", "1gb", "D2404031213486570202"],
        ["28", "2gb", "D2404031215315038594"],
        ["29", "500mb-dia", "D2404031211172035310"],
        ["29", "1gb", "D2404031213486570202"],
        ["29", "2gb", "D2404031215315038594"],
        ["30", "500mb-dia", "D2404031211172035310"],
        ["30", "1gb", "D2404031213486570202"],
        ["30", "2gb", "D2404031215315038594"],        
    ]
    
    list_cm_europe_premium = [
        ["5", "1gb", "D2206291850234693769"],
        ["5", "2gb", "D2206291855407008527"],
        ["6", "1gb", "D2206091135171925874"],
        ["6", "2gb", "D2206291856141314480"],
        ["7", "1gb", "D2206091135171925874"],
        ["7", "2gb", "D2206291856141314480"],
        ["8", "1gb", "D2206091135414428250"],
        ["8", "2gb", "D2206291857110154857"],
        ["9", "1gb", "D2206091135414428250"],
        ["9", "2gb", "D2206291857110154857"],
        ["10", "1gb", "D2206091135414428250"],
        ["10", "2gb", "D2206291857110154857"],
        ["11", "1gb", "D2206091136019095391"],
        ["11", "2gb", "D2206291857403368188"],
        ["12", "1gb", "D2206091136019095391"],
        ["12", "2gb", "D2206291857403368188"],
        ["13", "1gb", "D2206091136019095391"],
        ["13", "2gb", "D2206291857403368188"],
        ["14", "1gb", "D2206091136019095391"],
        ["14", "2gb", "D2206291857403368188"],
        ["15", "1gb", "D2206091136019095391"],
        ["15", "2gb", "D2206291857403368188"],
        ["16", "1gb", "D2206291851030076782"],
        ["16", "2gb", "D2206291858199844782"],
        ["17", "1gb", "D2206291851030076782"],
        ["17", "2gb", "D2206291858199844782"],
        ["18", "1gb", "D2206291851030076782"],
        ["18", "2gb", "D2206291858199844782"],
        ["19", "1gb", "D2206291851030076782"],
        ["19", "2gb", "D2206291858199844782"],
        ["20", "1gb", "D2206291851030076782"],
        ["20", "2gb", "D2206291858199844782"],
        ["21", "1gb", "D2206091136223123003"],
        ["21", "2gb", "D2206291858438338083"],
        ["22", "1gb", "D2206091136223123003"],
        ["22", "2gb", "D2206291858438338083"],
        ["23", "1gb", "D2206091136223123003"],
        ["23", "2gb", "D2206291858438338083"],
        ["24", "1gb", "D2206091136223123003"],
        ["24", "2gb", "D2206291858438338083"],
        ["25", "1gb", "D2206091136223123003"],
        ["25", "2gb", "D2206291858438338083"],
        ["26", "1gb", "D2206091136223123003"],
        ["26", "2gb", "D2206291858438338083"],
        ["27", "1gb", "D2206091136223123003"],
        ["27", "2gb", "D2206291858438338083"],
        ["28", "1gb", "D2206091136223123003"],
        ["28", "2gb", "D2206291858438338083"],
        ["29", "1gb", "D2206091136223123003"],
        ["29", "2gb", "D2206291858438338083"],
        ["30", "1gb", "D2206091136223123003"],
        ["30", "2gb", "D2206291858438338083"],
    ]
    
    tz = pytz.timezone("Europe/Lisbon")
    today = datetime.now(tz).date()

    logger.info('>>>>>>>>>> ATIVAÇÂO CM INICIADA')
    
    # Selecionar pedidos
    if id is None:
        orders_all = Orders.objects.filter(order_status='AA', id_sim__operator='CM', activation_date__lte=today)
    else:
        orders_all = Orders.objects.filter(pk=id)    
    
    if orders_all.count() == 0:
        logger.info('>>>>>>>>>> ATIVAÇÂO CM FINALIZADA')
        return    
    
    if orders_all != None:
        # Gerar Token
        api_token = ApiCM.get_token()
        
        if api_token == "error":
            logger.error('>>>>>>>>>> ERRO DE TOKEN')
            return
    
    for order in orders_all:
        
        # Aguardar 1 segundo
        time.sleep(0.5)
        
        order = Orders.objects.get(pk=order.id)
        order_id = order.order_id
        order_item = order.id
        order_product = order.product
        order_country = order.countries
        order_day = str(order.days)
        order_data = str(order.data_day)
        order_sim = order.id_sim.sim
        list_plan = []
        
        logger.info(f'>>>>>>>>>> ATIVANDO SIM {order_sim} - {order_id}')
        
        def errorData(data_dict=None):
            # Adicionar Nota
            note = f'Erro ao ativar o SIM {order_sim}. Verificar manualmente. ERRO: {data_dict}'
            NotesAdd.addNote(order, note)
            # Alterar status do sistema
            UpdateOrder.upStatus(order_item, 'EA')
        
        def generate_password_digest(app_secret):
            nonce = str(int(time.time() * 1000))
            created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            digest = base64.b64encode(hashlib.sha256((nonce + created + app_secret).encode('utf-8')).digest()).decode('utf-8')
            return nonce, created, digest
        
        # Definir lista
        if order_product == "chip-internacional-europa-plus" or order_product == "chip-internacional-europa":
            list_plan = list_cm_europe
        elif order_product == "chip-internacional-europa-premium":
            list_plan = list_cm_europe_premium
        elif order_product == "chip-internacional-global":
            if order_country == True:
                list_plan = list_cm_global_ch
            else:
                list_plan = list_cm_global
        elif order_product == "chip-internacional-eua-canada-e-mexico":
            list_plan = list_cm_north
        elif order_product == "chip-internacional-america-do-sul-premium":
            list_plan = list_cm_south
        
        # Selecionar plano
        sel_plan = [(order_day, order_data)]
        plan_code = None        
        for plan in list_plan:
            day, data, cod = plan
            if (day, data) in sel_plan:
                plan_code = cod
                break
        
        # Verificar se plan_code foi definido
        if plan_code is None:
            # Inserir nota e alterar status do sistema
            NotesAdd.addNote(order, f"Nenhum plano correspondente encontrado para {order_day} e {order_data}.")
            errorData()
            continue

        # URL do endpoint
        url_api = f'{settings.APICM_URL}/aep/APP_createOrder_SBO/v1'
        parsed_url = urlparse(url_api)
        app_key = settings.APICM_KEY
        app_secret = settings.APICM_SECRET

        # Gerar PasswordDigest
        nonce, created, password_digest = generate_password_digest(app_secret)

        # Cabeçalhos da requisição
        headers = {
            'Content-Type': 'application/json',
            "Accept": "application/json",
            "Authorization": 'WSSE realm="SDP", profile="UsernameToken", type="Appkey"',
            "X-WSSE": f'UsernameToken Username="{app_key}", PasswordDigest="{password_digest}", Nonce="{nonce}", Created="{created}"',
        }

        # Corpo da requisição
        payload = json.dumps({
            "accessToken": api_token,
            "dataBundleId": plan_code,
            "ICCID": order_sim,
            "thirdOrderId": order_item,
            "includeCard":"0",
            "is_Refuel":"1",
            "quantity":"1",
        })
        
        # Fazer a requisição POST com tempo limite
        conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, timeout=10)
        conn.request("POST", parsed_url.path, payload, headers)
        res = conn.getresponse()

        # Verificar o status da resposta
        data = res.read()
        
        if res.status != 200:
            errorData(data.decode("utf-8"))
        else:
            data_dict = json.loads(data)
            result_data = data_dict.get('description')
            if result_data != 'Success':
                errorData(data_dict)
            else:
                # Adicionar Nota
                note = f'SIM {order_sim} ativado na China Mobile.'
                NotesAdd.addNote(order, note)
                # Alterar status do sistema
                UpdateOrder.upStatus(order_item, 'AT')
                UpdateStore.upStore(
                    order_id = order_id,
                    item_id_store = order.item_id_store if order.item_id_store else None,
                    _status = 'AT',
                    status_g = 'AT',
                )

        conn.close()

    logger.info('>>>>>>>>>> ATIVAÇÂO CM FINALIZADA')


@shared_task(time_limit=110, soft_time_limit=100)
def simActivateMS(id=None):
    """
    Ativa SIMs da operadora **MoviStar (MS)** para pedidos com status ``AA``.

    Args:
        id (int, optional): PK do pedido a ativar. Se ``None``, processa em lote.

    Limites: ``soft_time_limit=100s``, ``time_limit=110s``.
    """
    # Timezone UTC+2h
    tz = pytz.timezone("Europe/Madrid")
    today = datetime.now(tz).date()
    # A lógica original busca até 2 dias no futuro, mantendo isso.
    activation_limit_date = today + timedelta(days=2)
    
    logger.info('>>>>>>>>>> ATIVAÇÂO MS INICIADA')

    # Selecionar pedidos
    if id is None:
        orders_to_process = Orders.objects.filter(
            order_status='AA', 
            id_sim__operator='MS', 
            activation_date__lte=activation_limit_date
        )
    else:
        orders_to_process = Orders.objects.filter(pk=id)
    
    if not orders_to_process.exists():
        logger.info('Nenhum pedido encontrado para ativação da MS.')
        return

    for order in orders_to_process:
        try:
            logger.info(f'Processando ativação para o pedido {order.order_id} (SIM: {order.id_sim.sim})')

            client_name_parts = order.client.split()
            last_name_1 = client_name_parts[0] if len(client_name_parts) > 0 else ''
            last_name_2 = client_name_parts[1] if len(client_name_parts) > 1 else ''
            
            passport_number = ''.join([str(random.randint(0, 9)) for _ in range(8)])

            client_email = order.email if order.email else "chip@acasadochip.com"
            
            payload = {
                "operator": 15,
                "product": 694,
                "phone_number": str(order.id_sim.sim),
                "extra_line": 0,
                "custom_email": True,
                "kyc": True,
                "activate_at": str(order.activation_date),
                "client": {
                    "name": str(last_name_1)[:50],
                    "last_name_1": str(last_name_2)[:50],
                    "last_name_2": "",
                    "email": client_email,
                    "document_type": 4,
                    "document_value": passport_number,
                    "date_birth": "1985-01-01",
                    "sex": "M",
                    "nationality": 170,
                    "cp": "28001",
                    "province": 32,
                    "locality": "locality",
                }
            }
            
            url = f"{settings.APIMS_URL}/api/activations/new"
            params = {'token': settings.APIMS_TOKEN}
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }

            response = requests.post(url, params=params, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            response_data = response.json()

            logger.info(f'Pedido {order.order_id} ativado com sucesso na MS.')
            UpdateOrder.upStatus(order.id, 'AT')
            UpdateStore.upStore(
                order_id = order.order_id,
                item_id_store = order.item_id_store if order.item_id_store else None,
                _status='AT',
                status_g = 'AT',
            )  
            NotesAdd.addNote(order, f'Pedido {order.order_id} ativado com sucesso na MS.)')

        except requests.exceptions.HTTPError as e:
            # CORREÇÃO: Captura o erro HTTP para extrair a mensagem da API.
            error_to_save = f"Erro HTTP {e.response.status_code}"
            log_message = f"Erro na API ao ativar o pedido {order.order_id}: {error_to_save}"
            
            try:
                # Tenta decodificar a resposta JSON da API
                error_details = e.response.json()
                log_message += f" Detalhes: {json.dumps(error_details)}"
                
                # Extrai a mensagem de erro específica para salvar no pedido
                api_message_str = error_details.get('message')
                if api_message_str:
                    try:
                        # A API retorna uma string JSON dentro do campo 'message'
                        parsed_message = json.loads(api_message_str)
                        error_to_save = ', '.join(parsed_message) if isinstance(parsed_message, list) else str(parsed_message)
                    except (json.JSONDecodeError, TypeError):
                        error_to_save = str(api_message_str)
                else:
                    error_to_save = json.dumps(error_details)

            except json.JSONDecodeError:
                # Se a resposta não for JSON, salva o texto bruto
                error_to_save = e.response.text
                log_message += f" Resposta não-JSON: {error_to_save}"

            logger.info(log_message)
            UpdateOrder.upStatus(order.id, 'EA')
            NotesAdd.addNote(order, f"{log_message}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conexão/HTTP ao ativar o pedido {order.order_id}: {e}")
            UpdateOrder.upStatus(order.id, 'EA')
            NotesAdd.addNote(order, f"Erro de comunicação com a API da Movistar ao tentar ativar o SIM {order.id_sim.sim}: {e}")
        
        except Exception as e:
            logger.error(f"Erro inesperado ao processar o pedido {order.order_id}: {e}", exc_info=True)
            UpdateOrder.upStatus(order.id, 'EA')
            NotesAdd.addNote(order, f"Ocorreu um erro interno no sistema ao tentar ativar o SIM {order.id_sim.sim}: {e}")

    logger.info('Tarefa de ativação de SIMs da Movistar (MS) finalizada.')
    

@shared_task(time_limit=110, soft_time_limit=100)
def simActivateSM(id=None): # Orange e AT&T
    """
    Ativa eSIMs da operadora **AT&T (AT)** e Orange (OR) para pedidos com status ``AA``.

    Usado para eSIMs de clientes com celular Samsung ou compatível com AT&T.

    Args:
        id (int, optional): PK do pedido a ativar. Se ``None``, processa em lote.

    Limites: ``soft_time_limit=100s``, ``time_limit=110s``.
    """
    # Timezone UTC+2h
    tz = pytz.timezone("America/Sao_Paulo")
    today = datetime.now(tz).date()
    # A lógica original busca até 2 dias no futuro, mantendo isso.
    activation_limit_date = today
    
    logger.info('>>>>>>>>>> ATIVAÇÂO SM INICIADA')

    # Selecionar pedidos
    if id is None:
        orders_to_process = Orders.objects.filter(
            order_status='AA', 
            id_sim__operator__in=['AT', 'OR'], 
            id_sim__in=[47282, 48138],
            activation_date__lte=activation_limit_date
        )
    else:
        orders_to_process = Orders.objects.filter(pk=id)
    
    if not orders_to_process.exists():
        return

    for order in orders_to_process:
        try:
            logger.info(f'Processando ativação para o pedido {order.order_id} (SIM: {order.id_sim.sim})')
            
            if order.data_day == '10-ilimitado':
                product_id = 20
            elif order.data_day == '30-ilimitado':
                product_id = 19
            elif order.data_day == 'world':
                # product_id = 7
                continue
            elif order.data_day == '20gb':
                product_id = 9
            elif order.data_day == '50gb':
                product_id = 4
            else:
                logger.error(f"Plano de dados desconhecido para o pedido {order.order_id}: {order.data_day}")
                UpdateOrder.upStatus(order.id, 'EA')
                NotesAdd.addNote(order, f"Plano de dados desconhecido para ativação na AT&T: {order.data_day}. Verificar manualmente.")
                continue
                     
            url = f"{settings.APISM_URL}/api/v1/order"
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {settings.APISM_TOKEN}",
            }
            payload = {
                "product_id": product_id,
            }               

            response = requests.post(url, headers=headers, data=payload, timeout=30)
            response.raise_for_status()
            response_data = response.json()
            
            status_now = response_data['status']['name']
            
            order_sim = response_data['id']
            order.order_sim = order_sim
            order.save()

            logger.info(f'Pedido {order.order_id} enviado com sucesso na AT&T/Orange')
            
            UpdateOrder.upStatus(order.id, 'AO')
            NotesAdd.addNote(order, f'Pedido {order.order_id} enviado com sucesso na AT&T/Orange. Aguardando retorno da operadora. STATUS ATUAL: {status_now}.')

        except requests.exceptions.HTTPError as e:
            # CORREÇÃO: Captura o erro HTTP para extrair a mensagem da API.
            error_to_save = f"Erro HTTP {e.response.status_code}"
            log_message = f"Erro na API ao ativar o pedido {order.order_id}: {error_to_save}"
            
            try:
                # Tenta decodificar a resposta JSON da API
                error_details = e.response.json()
                log_message += f" Detalhes: {json.dumps(error_details)}"
                
                # Extrai a mensagem de erro específica para salvar no pedido
                api_message_str = error_details.get('message')
                if api_message_str:
                    try:
                        # A API retorna uma string JSON dentro do campo 'message'
                        parsed_message = json.loads(api_message_str)
                        error_to_save = ', '.join(parsed_message) if isinstance(parsed_message, list) else str(parsed_message)
                    except (json.JSONDecodeError, TypeError):
                        error_to_save = str(api_message_str)
                else:
                    error_to_save = json.dumps(error_details)

            except json.JSONDecodeError:
                # Se a resposta não for JSON, salva o texto bruto
                error_to_save = e.response.text
                log_message += f" Resposta não-JSON: {error_to_save}"

            logger.info(log_message)
            UpdateOrder.upStatus(order.id, 'EA')
            NotesAdd.addNote(order, f"{log_message}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conexão/HTTP ao ativar o pedido {order.order_id}: {e}")
            UpdateOrder.upStatus(order.id, 'EA')
            NotesAdd.addNote(order, f"Erro de comunicação com a API da AT&T ao tentar ativar o SIM {order.id_sim.sim}: {e}")
        
        except Exception as e:
            logger.error(f"Erro inesperado ao processar o pedido {order.order_id}: {e}", exc_info=True)
            UpdateOrder.upStatus(order.id, 'EA')
            NotesAdd.addNote(order, f"Ocorreu um erro interno no sistema ao tentar ativar o SIM {order.id_sim.sim}: {e}")

    logger.info('>>>>>>>>>> ATIVAÇÂO SM FINALIZADA')
    
    
@shared_task(time_limit=110, soft_time_limit=100)
def simAgdOperator():
    from apps.sims.views.views import upload_file_to_s3
    
    orders = Orders.objects.filter(order_status='AO')
    
    if not orders.exists():
        logger.info('---------- Nenhum pedido encontrado para processamento.')
        return
    
    for order in orders:
                
        order_sim = order.order_sim
        order_product = order.product
        type_sim = order.type_sim
        data = order.data_day
        operator = order.id_sim.operator
        
        # Verificar de é AT&T
        if order_product not in operPlan.listPlan(operator):
            continue
        
        logger.info(f'Processando pedido {order.order_id} para consulta de status na AT&T/Orange.')
        
        try:
            url = f"{settings.APISM_URL}/api/v1/order/{order_sim}"
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {settings.APISM_TOKEN}",
            }
            payload = {
            }               

            response = requests.get(url, headers=headers, params=payload, timeout=30)
            response.raise_for_status()
            response_data = response.json()
            status_now = response_data['status']['name'] if 'status' in response_data and 'name' in response_data['status'] else 'Status desconhecido'
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erro HTTP ao consultar o status do pedido {order.order_id} na AT&T/Orange: {e}")
            continue
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conexão ao consultar o status do pedido {order.order_id} na AT&T/Orange: {e}")
            continue
        except Exception as e:
            logger.error(f"Erro inesperado ao consultar o status do pedido {order.order_id} na AT&T: {e}", exc_info=True)
            continue
        
        if status_now == 'completed':
            sim_value = response_data['products'][0]['sim_data']['iccid']
            lpa_value = response_data['products'][0]['sim_data']['lpa_code']
            
            try:
                # Converter e salvar SIM no estoque            
                qr_file = qrcodeChange.build_qr_file(lpa_value, sim_value)
                fileurl = upload_file_to_s3(qr_file).replace(f'https://{settings.AWS_S3_CUSTOM_DOMAIN}', '')
                add_sim = Sims(
                    sim=sim_value,
                    lpa=lpa_value,
                    link=fileurl,
                    type_sim=type_sim,
                    data=data,
                    operator=operator,
                    sim_status='AT',
                )
                add_sim.save()
                
                # Salvar SIM no pedido
                order.id_sim = add_sim
                order.save()
                
                # Alterar status do pedido
                UpdateOrder.upStatus(order.id, 'AT')
                UpdateStore.upStore(
                    order_id = order.order_id,
                    item_id_store = order.item_id_store if order.item_id_store else None,
                    _status='AT',
                    status_g = 'AT',
                )
                send_email_sims.delay(id=order.id)
                NotesAdd.addNote(order, f'Pedido {order.order_id} ativado com sucesso na AT&T. SIM: {sim_value}. STATUS ATUAL: {status_now}.')
            except Exception as e:
                logger.error(f"Erro ao processar o SIM para o pedido {order.order_id}: {e}", exc_info=True)
                UpdateOrder.upStatus(order.id, 'EA')
                NotesAdd.addNote(order, f"Ocorreu um erro interno no sistema ao processar o SIM para o pedido {order.order_id}: {e}")
            
        else:
            continue
        

@shared_task(time_limit=110, soft_time_limit=100)
def simActivateOR(id=None):
    """
    Ativa SIMs da operadora **Orange (OR)** para pedidos com status ``AA``.

    Args:
        id (int, optional): PK do pedido a ativar. Se ``None``, processa todos
            os pedidos com status ``AA`` e operadora ``OR`` com data <= amanhã.

    Limites: ``soft_time_limit=100s``, ``time_limit=110s``.
    """
    tz = pytz.timezone(settings.TIME_ZONE)
    today = datetime.now(tz).date()
    tomorrow = today + timedelta(days=1)

    logger.info(f'>>>>>>>>>> ATIVAÇÂO OR INICIADA')
    logger.info(
        'Janela de ativação OR | timezone=%s | today=%s | tomorrow=%s | id=%s',
        settings.TIME_ZONE,
        today,
        tomorrow,
        id,
    )
    
    # Selecionar pedidos
    if id is None:
        orders_all = Orders.objects.filter(order_status='AA', id_sim__operator='OR', activation_date__lte=tomorrow)
        logger.info(
            'Consulta OR executada | filtros: status=AA, operator=OR, activation_date<=%s | total=%s',
            tomorrow,
            orders_all.count(),
        )
    else:
        orders_all = Orders.objects.filter(pk=id)
        logger.info('Consulta OR por id executada | id=%s | encontrado=%s', id, orders_all.exists())
    
    if not orders_all.exists():
        logger.info('>>>>>>>>>> ATIVAÇÂO OR FINALIZADA')
        return

    ids_preview = list(orders_all.values_list('id', flat=True)[:20])
    logger.info('Pedidos OR selecionados (primeiros 20 ids): %s', ids_preview)
           
    for order in orders_all:
        
        logger.info(
            'Processando OR | order_id=%s | id_item=%s | sim_id=%s | sim=%s | type_sim=%s | data_day=%s | activation_date=%s',
            order.order_id,
            order.id,
            order.id_sim_id,
            order.id_sim.sim,
            order.id_sim.type_sim if order.id_sim else None,
            order.data_day,
            order.activation_date,
        )
        order = Orders.objects.get(pk=order.id)
        id_item = order.id
        order_id = order.order_id
        
        # ORANGE: Ativação automática para eSIM específico
        if order.id_sim.type_sim == 'esim' and order.data_day == 'world' and order.id_sim_id==48138:  # SIM específico para ativação automática OR
            logger.info('Branch OR especial acionado | order_id=%s | sim_id=%s', order.order_id, order.id_sim_id)
            sim_ds = Sims.objects.all().order_by('id').filter(operator='OR', type_sim='esim', sim_status='DS', data='world').first()
            if sim_ds is None:
                logger.error(
                    'Sem SIM DS disponível para branch OR especial | order_id=%s | filtros: operator=OR,type_sim=esim,sim_status=DS,data=world',
                    order.order_id,
                )
                continue
            sim_put = Sims.objects.get(pk=sim_ds.id)
            sim_put.sim_status = 'AT'
            sim_put.save()
            logger.info('SIM substituto ativado | order_id=%s | novo_sim_id=%s | novo_sim=%s', order.order_id, sim_put.id, sim_put.sim)
            
            time.sleep(1)
            
            order_put = Orders.objects.get(pk=order.id)
            order_put.id_sim_id = sim_ds.id            
            order_put.save()
            logger.info('Pedido atualizado com novo SIM OR especial | order_id=%s | novo_sim_id=%s', order.order_id, sim_ds.id)
        elif order.id_sim_id == 48138:
            logger.info(
                'Pedido ignorado por regra OR especial | order_id=%s | sim_id=%s | motivo=data_day/type_sim fora da regra',
                order.order_id,
                order.id_sim_id,
            )
            continue
            
        send_email_sims.delay(order.id)
        logger.info('E-mail de ativação enfileirado | order_id=%s', order.order_id)
        
        
        # Alterar status
        UpdateOrder.upStatus(id_item,'AT')
        UpdateStore.upStore(
            order_id = order_id,
            item_id_store = order.item_id_store if order.item_id_store else None,
            _status = 'AT',
            status_g = 'AT',
        )            
        # Adicionar nota
        NotesAdd.addNote(order,f'eSIM Ativado - Processo automático')
        logger.info('Pedido finalizado em OR | order_id=%s | status_final=AT', order.order_id)
        
                
    logger.info('>>>>>>>>>> ATIVAÇÂO OR FINALIZADA')


    
    

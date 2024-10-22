from urllib.parse import urlparse
from celery import shared_task
import os
import http.client
import json
import time
from django.conf import settings
from .classes import ApiTC
from apps.orders.models import Orders, Notes
from apps.orders.classes import ApiStore, StatusStore, NotesAdd, UpdateOrder
from apps.send_email.tasks import send_email_sims
from apps.sims.models import Sims
from datetime import datetime, timedelta
import pytz
import pandas as pd

@shared_task
def sims_in_orders():
    
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
        esim_eua = type_sim_i == 'esim' and (product_i == 'chip-internacional-eua' or product_i == 'chip-internacional-eua-30-dias')
        esim_ok = type_sim_i == 'esim' and (product_i != 'chip-internacional-eua' or product_i != 'chip-internacional-eua-30-dias')
        
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

            # ESCOLHER OPERADORA
            if (product_i == 'chip-internacional-europa' and countries_i == False) or product_i == 'chip-internacional-america-do-sul':
                operator_i = 'TC'
            elif product_i == 'chip-internacional-eua' or product_i == 'chip-internacional-eua-30-dias':
                operator_i = 'TM'
            else: operator_i = 'CM'
            
            # Select SIM
            if esim_eua:
                sim_ds = Sims.objects.all().get(pk=0)
            else:
                sim_ds = Sims.objects.all().order_by('id').filter(operator=operator_i, type_sim=type_sim_i, sim_status='DS').first()
                if sim_ds:
                    pass
                else:
                    print('>>>>>>>>>>>>>>>>>>>>>>> SIMs indisponíveis!')
                    continue
            
            # update order
            # Save SIMs
            if type_sim_i == 'esim':
                if product_i == 'chip-internacional-eua' or product_i == 'chip-internacional-eua-30-dias': status_ord = 'AI'
                else: status_ord = 'EE'
            else: status_ord = 'ES'
            
            order_put = Orders.objects.get(pk=id_id_i)
            order_put.id_sim_id = sim_ds.id            
            order_put.order_status = status_ord
            order_put.save()
            
            # Verification esim x eua
            if esim_eua:
                send_email_sims.delay(id_id_i)
                addNote(f'eSIM EUA - SIM padrão adicionado')
                msg_info.append(f'Pedido {order_id_i} atualizados com sucesso')
                continue
            
            # update sim
            sim_put = Sims.objects.get(pk=sim_ds.id)
            sim_put.sim_status = 'AT'
            sim_put.save()
            sim_e = sim_put.sim 
            
            addNote(f'(e)SIM {sim_e} adicionado')
            
            status_sis_site = StatusStore.st_sis_site()
            if status_ord in status_sis_site:
                update_store = {
                    'status': status_sis_site[status_ord]
                }
    
            apiStore = ApiStore.conectApiStore()                    
            apiStore.put(f'orders/{order_id_i}', update_store).json()
            
            msg_info.append(f'Pedido {order_id_i} atualizados com sucesso')
            
            n_item_total += 1
    
        print('>>>>>>>>>>>>>>>>>>>>>>> SIMs atribuidos!')
    
@shared_task
def simActivateTC(id=None):
    
    from apps.orders.tasks import up_order_st_store    
        
    london_tz = pytz.timezone('Europe/London')
    today = datetime.now(london_tz).date()

    print('>>>>>>>>>> ATIVAÇÂO INICIADA')
    
    # Selecionar pedidos
    if id is None:
        orders_all = Orders.objects.filter(order_status='AA', id_sim__operator='TC', activation_date__lte=today)
    else:
        orders_all = Orders.objects.filter(pk=id)
            
    # Checar conexão com API
    def error_api():
        print('>>>>>>>>>> ERRO API')
        # Checar Status
        UpdateOrder.upStatus(id_item,'EA')
        # Adicionar nota
        NotesAdd.addNote(order,f'{iccid} com erro na Telcon. Verificar erro.')
        error = 'error_apiResult'
        return error     
    
    for order in orders_all:
        
        order = Orders.objects.get(pk=order.id)
        order_id = order.order_id
        id_item = order.id
        try:
            iccid = order.id_sim.sim
        except Exception:
            iccid = None
            continue
        dataDay = order.data_day
        product = order.product
        
        # Variaveis globais        
        endpointId = None
        simStatus = None
        note = ''
        process = False
        token_api = None  
        
        # Verificar EndPointID / Status
        try:
            token_api = ApiTC.get_token()
            conn = http.client.HTTPSConnection(settings.APITC_HTTPCONN)
            headers = ApiTC.get_headers(token_api)
            get_iccid = ApiTC.get_iccid(iccid, headers)
            endpointId = get_iccid[0]
            simStatus = get_iccid[1]
            print('>>>>>>>>>> endpointId',endpointId)
            print('>>>>>>>>>> simStatus',simStatus)  
        except Exception:            
            error_api()
            continue
        ##
        
        # Alterar plano
        ApiTC.planChange(endpointId,headers,dataDay, product)
        NotesAdd.addNote(order,f'{iccid} Plano alterado para {dataDay}')    

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
                print('simStatus == Active')
                # Adicionar nota
                NotesAdd.addNote(order,f'{iccid} já estava ativado na Telcon')
                # Alterar Status
                UpdateOrder.upStatus(id_item,'AT')
                continue
            
            elif simStatus == 'Suspended':
                print('simStatus == Suspended')
                payload = json.dumps({
                    "Request": {
                        "endPointId": f"{endpointId}",
                        "requestParam": {
                            "lifeCycle": "A",
                            "reason": "1"
                        }
                    }
                })
                conn.request("POST", "/api/EndPointLifeCycleChange", payload, headers)
                # Adicionar nota
                note = f'{iccid} reativado com sucesso na Telcon'
                
                process = True
                
            else:
                print('simStatus == Other')
                # Alterar status
                UpdateOrder.upStatus(id_item,'EA')
                NotesAdd.addNote(order,f'{iccid} com erro na Telcon. Verificar erro.')
                continue
        
        if process == True:            
            
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
            
            print('>>>>>>>>>> resultCode', resultCode)
            print('>>>>>>>>>> resultDescription', resultDescription)
            
            if resultCode == 0:
                # Alterar status
                UpdateOrder.upStatus(id_item,'AT')
                up_order_st_store.delay(order_id,'ativado')
                # Adicionar nota
                NotesAdd.addNote(order,f'{note} TC: {resultDescription}')
            else:
                # Alterar status
                UpdateOrder.upStatus(id_item,'EA')
                # Adicionar nota
                NotesAdd.addNote(order,f'TC: {resultDescription}')
        
        # Fecha a conexão
        conn.close()
                
    print('>>>>>>>>>> ATIVAÇÂO FINALIZADA')


@shared_task
def simDeactivateTC(id=None):
    
    from apps.orders.tasks import up_order_st_store    
    
    timezone = pytz.timezone('Europe/London')
    min_hour = 23  # hora
    min_minute = 45  # 45 minutos

    current_hour = datetime.now(timezone).hour
    current_minute = datetime.now(timezone).minute
            
    # Timezone / Hoje
    today = pd.Timestamp.now(tz=timezone).date()

    # Selecionar pedidos
    if id is None:
        if current_hour < min_hour or (current_hour == min_hour and current_minute < min_minute):
            # Se for depois da hora mínima, execute a tarefa
            return
        else:
            orders_all = Orders.objects.filter(order_status='AT', id_sim__operator='TC')
    else:
        orders_all = Orders.objects.filter(pk=id)
        
    # Se não houver pedidos, encerre a execução
    if not orders_all.exists():
        print('Não há pedidos que correspondam aos critérios de filtro.')
        return
    
    fields_df = ['id', 'order_id', 'id_sim__sim', 'days', 'activation_date']
    orders_df = pd.DataFrame((orders_all.values(*fields_df)))
    orders_df['activation_date'] = pd.to_datetime(orders_df['activation_date'])
    orders_df['return_date'] = orders_df['activation_date'] + pd.to_timedelta(orders_df['days'], unit='d') - pd.to_timedelta(1, unit='d')

    if id is None:
        orders_df = orders_df.loc[orders_df['return_date'].dt.date == today]
    
    # Verificar se há pedidos para desativar
    if orders_df is None:
        print('>>>>>>>>>> Nenhum pedido para desativar')
        return
    
    def error_api():
        print('>>>>>>>>>> ERRO API')
        # Alterar status
        UpdateOrder.upStatus(id_item,'ED')
        # Adicionar nota
        NotesAdd.addNote(order,f'{iccid} com erro na Telcon. Verificar erro.')
        error = 'error_api Result'
        return error       

    print('>>>>>>>>>> DESATIVAÇÂO INICIADA')
    
    for index, o in orders_df.iterrows():
        
        order = Orders.objects.get(pk=o['id'])
        order_id = order.order_id
        id_item = order.id
        iccid = order.id_sim.sim
        
        note = ''
        resultCode = None
        resultDescription = None        
        endpointId = None
        simStatus = None
        token_api = None    
         
        # Get EndPointID / Status
        try:
            # Gerar tokem de acesso a API
            token_api = ApiTC.get_token()
            conn = http.client.HTTPSConnection(settings.APITC_HTTPCONN)
            headers = ApiTC.get_headers(token_api, cookie=True)
            get_iccid = ApiTC.get_iccid(iccid, headers)
            endpointId = get_iccid[0]
            simStatus = get_iccid[1] 
        except Exception:            
            error_api()
            continue      
        ##

        # Variaveis globais
        payload = json.dumps({
            "Request": {
                "endPointId": f"{endpointId}",
                "requestParam": {
                    "lifeCycle": "S",
                    "reason": "1"
                }
            }
        })
        
        conn.request("POST", "/api/EndPointLifeCycleChange", payload, headers)
        # Adicionar nota
            
        res = conn.getresponse()
        data = json.loads(res.read())
        try:
            resultCode = int(data["Response"]["resultCode"])
            resultDescription = data["Response"]["resultParam"]["resultDescription"]
        except Exception:
            resultCode = None
            resultDescription = None

        if resultCode == 0:
            if id is None:
                print('>>>>>>>>>> Alterar status')                
                # Alterar status                
                UpdateOrder.upStatus(id_item,'DE')
                up_order_st_store.delay(order.id,'desativado')
                sim_put = Sims.objects.get(pk=order.id_sim.id)
                sim_put.sim_status = 'DE'
                sim_put.save()
            # Adicionar nota
            NotesAdd.addNote(order,f'{iccid} desativado com sucesso na Telcon. TC: {resultDescription}')
        else:
            print('>>>>>>>>>> ERRO DESATIVADO')
            if id is None:
                # Alterar status
                UpdateOrder.upStatus(id_item,'ED')
            # Adicionar nota
            NotesAdd.addNote(order,f'{iccid} com erro na Telcon. Verificar erro. TC: {resultDescription}')
        
        # Fecha a conexão
        conn.close()
                
    print('>>>>>>>>>> DESATIVAÇÂO FINALIZADA')


@shared_task
def simActivateTM(id=None):
    
    from apps.orders.tasks import up_order_st_store    
        
    london_tz = pytz.timezone('Europe/London')
    today = datetime.now(london_tz).date()

    print('>>>>>>>>>> ATIVAÇÂO INICIADA')
    
    # Selecionar pedidos
    if id is None:
        orders_all = Orders.objects.filter(order_status='AA', id_sim__operator='TM', activation_date__lte=today)
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
                
        # Dados para a solicitação
        url = "https://usasimactivation.com/activation/index/submit"
        parsed_url = urlparse(url)
        payload = json.dumps({
            "active_time": activation_date.strftime("%Y-%m-%d"),
            "sim": iccid,
            "plan": "$50",
            "day": days,
            "imei": imei,
            "area": "",
            "customer_email": "",
            "comment": "",
            "carrier": "T-Mobile",
            "token": "ba8cbf5fd3c288c21d6725b532f04d73"
        })        
        
        # Cabeçalhos da solicitação
        headers = {
            'Content-Type': 'application/json'
        }
        # Estabelece a conexão HTTPS
        conn = http.client.HTTPSConnection(parsed_url.netloc)
        # Envia a solicitação POST
        conn.request("POST", parsed_url.path, payload, headers)
        # Obtém a resposta
        res = conn.getresponse()
        data = res.read()
        # Decodifica a resposta
        response_data = json.loads(data.decode("utf-8"))
        # Verifica o código de resposta
        if 'code' in response_data:
            if response_data['code'] == 0:
                # Alterar status
                UpdateOrder.upStatus(id_item,'AT')
                up_order_st_store.delay(order_id,'ativado')
                # Adicionar nota
                NotesAdd.addNote(order,f'{iccid} Enviado para ativação na T-Mobile')
            else:
                # Alterar status
                UpdateOrder.upStatus(id_item,'EA')
                # Adicionar nota
                NotesAdd.addNote(order,f'Houve um erro ao ativar o SIM {iccid}. Verificar manualmente.')
        else:
            # Alterar status
            UpdateOrder.upStatus(id_item,'EA')
            # Adicionar nota
            NotesAdd.addNote(order,f'Código não identificado ao ativar o SIM {iccid}. Verificar manualmente.')

        # Fecha a conexão
        conn.close()
        
                
    print('>>>>>>>>>> ATIVAÇÂO TM FINALIZADA')


@shared_task
def simActivateCM(id=None):
    from apps.orders.tasks import up_order_st_store    

    list_cm_europe = [
        ["5", "500mb-dia", "D181029093919_215465"],
        ["5", "1gb", "D2206291850234693769"],
        ["5", "2gb", "D2206291855407008527"],
        ["6", "500mb-dia", "D181029093919_215465"],
        ["6", "1gb", "D2206291850234693769"],
        ["6", "2gb", "D2206291855407008527"],
        ["7", "500mb-dia", "D181029102028_215672"],
        ["7", "1gb", "D2206091135171925874"],
        ["7", "2gb", "D2206291856141314480"],
        ["8", "500mb-dia", "D181029102028_215672"],
        ["8", "1gb", "D2206091135171925874"],
        ["8", "2gb", "D2206291856141314480"],
        ["9", "500mb-dia", "D181029102028_215672"],
        ["9", "1gb", "D2206091135171925874"],
        ["9", "2gb", "D2206291856141314480"],
        ["10", "500mb-dia", "D181029103013_215724"],
        ["10", "1gb", "D2206091135414428250"],
        ["10", "2gb", "D2206291857110154857"],
        ["11", "500mb-dia", "D181029103013_215724"],
        ["11", "1gb", "D2206091135414428250"],
        ["11", "2gb", "D2206291857110154857"],
        ["12", "500mb-dia", "D181029103013_215724"],
        ["12", "1gb", "D2206091135414428250"],
        ["12", "2gb", "D2206291857110154857"],
        ["13", "500mb-dia", "D181029103013_215724"],
        ["13", "1gb", "D2206091135414428250"],
        ["13", "2gb", "D2206291857110154857"],
        ["14", "500mb-dia", "D181029103013_215724"],
        ["14", "1gb", "D2206091135414428250"],
        ["14", "2gb", "D2206291857110154857"],
        ["15", "500mb-dia", "D181029103956_215769"],
        ["15", "1gb", "D2206091136019095391"],
        ["15", "2gb", "D2206291857403368188"],
        ["16", "500mb-dia", "D181029103956_215769"],
        ["16", "1gb", "D2206091136019095391"],
        ["16", "2gb", "D2206291857403368188"],
        ["17", "500mb-dia", "D181029103956_215769"],
        ["17", "1gb", "D2206091136019095391"],
        ["17", "2gb", "D2206291857403368188"],
        ["18", "500mb-dia", "D181029103956_215769"],
        ["18", "1gb", "D2206091136019095391"],
        ["18", "2gb", "D2206291857403368188"],
        ["19", "500mb-dia", "D181029103956_215769"],
        ["19", "1gb", "D2206091136019095391"],
        ["19", "2gb", "D2206291857403368188"],
        ["20", "500mb-dia", "D181029104429_215812"],
        ["20", "1gb", "D2206291851030076782"],
        ["20", "2gb", "D2206291858199844782"],
        ["21", "500mb-dia", "D181029104429_215812"],
        ["21", "1gb", "D2206291851030076782"],
        ["21", "2gb", "D2206291858199844782"],
        ["22", "500mb-dia", "D181029104429_215812"],
        ["22", "1gb", "D2206291851030076782"],
        ["22", "2gb", "D2206291858199844782"],
        ["23", "500mb-dia", "D181029104429_215812"],
        ["23", "1gb", "D2206291851030076782"],
        ["23", "2gb", "D2206291858199844782"],
        ["24", "500mb-dia", "D181029104429_215812"],
        ["24", "1gb", "D2206291851030076782"],
        ["24", "2gb", "D2206291858199844782"],
        ["25", "500mb-dia", "D181029104429_215812"],
        ["25", "1gb", "D2206291851030076782"],
        ["25", "2gb", "D2206291858199844782"],
        ["26", "500mb-dia", "D181029104429_215812"],
        ["26", "1gb", "D2206291851030076782"],
        ["26", "2gb", "D2206291858199844782"],
        ["27", "500mb-dia", "D181029104429_215812"],
        ["27", "1gb", "D2206291851030076782"],
        ["27", "2gb", "D2206291858199844782"],
        ["28", "500mb-dia", "D181029104429_215812"],
        ["28", "1gb", "D2206291851030076782"],
        ["28", "2gb", "D2206291858199844782"],
        ["29", "500mb-dia", "D181029104429_215812"],
        ["29", "1gb", "D2206291851030076782"],
        ["29", "2gb", "D2206291858199844782"],
        ["30", "500mb-dia", "D181029105247_215857"],
        ["30", "1gb", "D2206091136223123003"],
        ["30", "2gb", "D2206291858438338083"],
    ]

    list_cm_global = [
        ["5", "500mb-dia", "D181031181258_229560"],
        ["5", "1gb", "D2206301156230194956"],
        ["5", "2gb", "D2206301205165738953"],
        ["6", "500mb-dia", "D181031181258_229560"],
        ["6", "1gb", "D2206301156230194956"],
        ["6", "2gb", "D2206301205165738953"],
        ["7", "500mb-dia", "D181031181914_229650"],
        ["7", "1gb", "D2206091105276234237"],
        ["7", "2gb", "D2206301205486118193"],
        ["8", "500mb-dia", "D181031181914_229650"],
        ["8", "1gb", "D2206091105276234237"],
        ["8", "2gb", "D2206301205486118193"],
        ["9", "500mb-dia", "D181031181914_229650"],
        ["9", "1gb", "D2206091105276234237"],
        ["9", "2gb", "D2206301205486118193"],
        ["10", "500mb-dia", "D181031182542_229740"],
        ["10", "1gb", "D2206091107307032864"],
        ["10", "2gb", "D2206301206197251946"],
        ["11", "500mb-dia", "D181031182542_229740"],
        ["11", "1gb", "D2206091107307032864"],
        ["11", "2gb", "D2206301206197251946"],
        ["12", "500mb-dia", "D181031182542_229740"],
        ["12", "1gb", "D2206091107307032864"],
        ["12", "2gb", "D2206301206197251946"],
        ["13", "500mb-dia", "D181031182542_229740"],
        ["13", "1gb", "D2206091107307032864"],
        ["13", "2gb", "D2206301206197251946"],
        ["14", "500mb-dia", "D181031182542_229740"],
        ["14", "1gb", "D2206091107307032864"],
        ["14", "2gb", "D2206301206197251946"],
        ["15", "500mb-dia", "D181031183135_229830"],
        ["15", "1gb", "D2206091108433606607"],
        ["15", "2gb", "D2206301206528368501"],
        ["16", "500mb-dia", "D181031183135_229830"],
        ["16", "1gb", "D2206091108433606607"],
        ["16", "2gb", "D2206301206528368501"],
        ["17", "500mb-dia", "D181031183135_229830"],
        ["17", "1gb", "D2206091108433606607"],
        ["17", "2gb", "D2206301206528368501"],
        ["18", "500mb-dia", "D181031183135_229830"],
        ["18", "1gb", "D2206091108433606607"],
        ["18", "2gb", "D2206301206528368501"],
        ["19", "500mb-dia", "D181031183135_229830"],
        ["19", "1gb", "D2206091108433606607"],
        ["19", "2gb", "D2206301206528368501"],
        ["20", "500mb-dia", "D210521035722_568094"],
        ["20", "1gb", "D2206301157034705599"],
        ["20", "2gb", "D2206301207302789206"],
        ["21", "500mb-dia", "D210521035722_568094"],
        ["21", "1gb", "D2206301157034705599"],
        ["21", "2gb", "D2206301207302789206"], 
        ["22", "500mb-dia", "D210521035722_568094"],
        ["22", "1gb", "D2206301157034705599"],
        ["22", "2gb", "D2206301207302789206"], 
        ["23", "500mb-dia", "D210521035722_568094"],
        ["23", "1gb", "D2206301157034705599"],
        ["23", "2gb", "D2206301207302789206"], 
        ["24", "500mb-dia", "D210521035722_568094"],
        ["24", "1gb", "D2206301157034705599"],
        ["24", "2gb", "D2206301207302789206"], 
        ["25", "500mb-dia", "D210521075722_568297"],
        ["25", "1gb", "D2206301157335495089"],
        ["25", "2gb", "D2206301207564086363"], 
        ["26", "500mb-dia", "D210521075722_568297"],
        ["26", "1gb", "D2206301157335495089"],
        ["26", "2gb", "D2206301207564086363"],  
        ["27", "500mb-dia", "D210521075722_568297"],
        ["27", "1gb", "D2206301157335495089"],
        ["27", "2gb", "D2206301207564086363"],  
        ["28", "500mb-dia", "D210521075722_568297"],
        ["28", "1gb", "D2206301157335495089"],
        ["28", "2gb", "D2206301207564086363"],  
        ["29", "500mb-dia", "D210521075722_568297"],
        ["29", "1gb", "D2206301157335495089"],
        ["29", "2gb", "D2206301207564086363"],
        ["30", "500mb-dia", "D181031183714_229920"],
        ["30", "1gb", "D2206091109242038213"],
        ["30", "2gb", "D2206301208289772531"],
    ]
    
    list_cm_global_ch = [
        ["5", "500mb-dia", "D181030042539_227624"],
        ["5", "1gb", "D2205171902194598628"],
        ["5", "2gb", "D2206301059342263262"],
        ["6", "500mb-dia", "D181031181258_229560"],
        ["6", "1gb", "D2206301156230194956"],
        ["6", "2gb", "D2206301205165738953"],
        ["7", "500mb-dia", "D181030043319_227719"],
        ["7", "1gb", "D2205171902519779100"],
        ["7", "2gb", "D2206301100122278918"],
        ["8", "500mb-dia", "D181030043319_227719"],
        ["8", "1gb", "D2205171902519779100"],
        ["8", "2gb", "D2206301100122278918"],
        ["9", "500mb-dia", "D181030043319_227719"],
        ["9", "1gb", "D2205171902519779100"],
        ["9", "2gb", "D2206301100122278918"],
        ["10", "500mb-dia", "D181030044052_227812"],
        ["10", "1gb", "D2205171903285254520"],
        ["10", "2gb", "D2206301100537072952"],
        ["11", "500mb-dia", "D181030044052_227812"],
        ["11", "1gb", "D2205171903285254520"],
        ["11", "2gb", "D2206301100537072952"],
        ["12", "500mb-dia", "D181030044052_227812"],
        ["12", "1gb", "D2205171903285254520"],
        ["12", "2gb", "D2206301100537072952"],
        ["13", "500mb-dia", "D181030044052_227812"],
        ["13", "1gb", "D2205171903285254520"],
        ["13", "2gb", "D2206301100537072952"],
        ["14", "500mb-dia", "D181030044052_227812"],
        ["14", "1gb", "D2205171903285254520"],
        ["14", "2gb", "D2206301100537072952"],
        ["15", "500mb-dia", "D181030060952_227953"],
        ["15", "1gb", "D2205171904079201878"],
        ["15", "2gb", "D2206301101255910272"],
        ["16", "500mb-dia", "D181030060952_227953"],
        ["16", "1gb", "D2205171904079201878"],
        ["16", "2gb", "D2206301101255910272"],
        ["17", "500mb-dia", "D181030060952_227953"],
        ["17", "1gb", "D2205171904079201878"],
        ["17", "2gb", "D2206301101255910272"],
        ["18", "500mb-dia", "D181030060952_227953"],
        ["18", "1gb", "D2205171904079201878"],
        ["18", "2gb", "D2206301101255910272"],
        ["19", "500mb-dia", "D181030060952_227953"],
        ["19", "1gb", "D2205171904079201878"],
        ["19", "2gb", "D2206301101255910272"],
        ["20", "500mb-dia", "D210520111201_567505"],
        ["20", "1gb", "D2205171904426262385"],
        ["20", "2gb", "D2206301102116254489"],
        ["21", "500mb-dia", "D210520111201_567505"],
        ["21", "1gb", "D2205171904426262385"],
        ["21", "2gb", "D2206301102116254489"], 
        ["22", "500mb-dia", "D210520111201_567505"],
        ["22", "1gb", "D2205171904426262385"],
        ["22", "2gb", "D2206301102116254489"], 
        ["23", "500mb-dia", "D210520111201_567505"],
        ["23", "1gb", "D2205171904426262385"],
        ["23", "2gb", "D2206301102116254489"], 
        ["24", "500mb-dia", "D210520111201_567505"],
        ["24", "1gb", "D2205171904426262385"],
        ["24", "2gb", "D2206301102116254489"], 
        ["25", "500mb-dia", "D210521020847_567890"],
        ["25", "1gb", "D2205171905123822954"],
        ["25", "2gb", "D2206301102507299017"], 
        ["26", "500mb-dia", "D210521020847_567890"],
        ["26", "1gb", "D2205171905123822954"],
        ["26", "2gb", "D2206301102507299017"],  
        ["27", "500mb-dia", "D210521020847_567890"],
        ["27", "1gb", "D2205171905123822954"],
        ["27", "2gb", "D2206301102507299017"],  
        ["28", "500mb-dia", "D210521020847_567890"],
        ["28", "1gb", "D2205171905123822954"],
        ["28", "2gb", "D2206301102507299017"],  
        ["29", "500mb-dia", "D210521020847_567890"],
        ["29", "1gb", "D2205171905123822954"],
        ["29", "2gb", "D2206301102507299017"],
        ["30", "500mb-dia", "D181030062003_228049"],
        ["30", "1gb", "D2205171905428070570"],
        ["30", "2gb", "D2206301103268430586"],
    ]
    
        
    london_tz = pytz.timezone('Europe/London')
    today = datetime.now(london_tz).date()

    print('>>>>>>>>>> ATIVAÇÂO CM INICIADA')
    
    # Selecionar pedidos
    if id is None:
        orders_all = Orders.objects.filter(order_status='AA', id_sim__operator='CM', activation_date__lte=today)
    else:
        orders_all = Orders.objects.filter(pk=id)
    
    for order in orders_all:    
        
        order = Orders.objects.get(pk=order.id)
        order_id = order.order_id
        order_item = order.id
        order_product = order.product
        order_country = order.countries
        order_day = order.data_day
        order_data = order.data_day
        order_sim = order.id_sim.sim
        
        # Definir lista
        if order_product == "chip-internacional-europa":
            list_plan = list_cm_europe
        elif order_product == "chip-internacional-global":
            if order_country == True:
                list_plan = list_cm_global_ch
            else:
                list_plan = list_cm_global
        
        # Selecionar plano
        sel_plan = [(order_day, order_data)]
        for plan in list_plan:
            day, data, cod = plan
            if (day, data) in sel_plan:
                plan_code = cod
                

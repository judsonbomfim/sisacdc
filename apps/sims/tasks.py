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
from datetime import datetime
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
        esim_eua = type_sim_i == 'esim' and product_i == 'chip-internacional-eua'
        esim_ok = type_sim_i == 'esim' and product_i != 'chip-internacional-eua'
                
        if ord.id_sim != None:
            if ord.order_status == 'AS':
                sim_put = Sims.objects.get(pk=id_id_i)
                if esim_eua:
                    sim_put.sim_status = 'AI'
                else:
                    sim_put.sim_status = 'AA'
                sim_put.save()
        else:    
            # Notes
            def addNote(t_note):
                add_sim = Notes( 
                    id_item = Orders.objects.get(pk=id_id_i),
                    note = t_note,
                    type_note = 'S',
                )
                add_sim.save()

            # Escolher operadora
            # if product_i == 'chip-internacional-europa' and countries_i == False and type_sim_i == 'esim':
            if product_i == 'chip-internacional-europa' and countries_i == False:
                operator_i = 'TC'
            elif product_i == 'chip-internacional-eua':
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
                if product_i == 'chip-internacional-eua': status_ord = 'AI'
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
            # Enviar eSIM para site
            if esim_ok:
                url_painel = str(os.getenv('URL_PAINEL'))
                esims_order = Orders.objects.filter(order_id=order_id_i).filter(type_sim='esim')
                esims_list = ''
                for esims_o in esims_order:
                    try:
                        link_sim = esims_o.id_sim.link              
                        esims_list = esims_list + f"<img src='{url_painel}{link_sim}' style='width: 300px; margin:40px;'>"
                        update_store = {
                            "meta_data":[
                                {
                                    "key": "campo_esims",
                                    "value": esims_list
                                },
                            ]
                        }
                    except:
                        update_store = {
                            "meta_data":[
                                {
                                    "key": "campo_esims",
                                    "value": ''
                                },
                            ]
                        }
                
            apiStore = ApiStore.conectApiStore()                    
            apiStore.put(f'orders/{order_id_i}', update_store).json()
            
            msg_info.append(f'Pedido {order_id_i} atualizados com sucesso')
            
            n_item_total += 1
    
        print('>>>>>>>>>>>>>>>>>>>>>>> SIMs atribuidos!')
    
@shared_task
def simActivateTC(id=None):
        
    london_tz = pytz.timezone('Europe/London')
    today = datetime.now(london_tz).date()

    print('>>>>>>>>>> ATIVAÇÂO INICIADA')
    
    # Select Orders
    if id == None:
        orders_all = Orders.objects.filter(order_status='AA', id_sim__operator='TC', activation_date=today)
    else:
        orders_all = Orders.objects.get(pk=id)
        
    def errorAPI():
        print('>>>>>>>>>> ERRO API')
        # Change Status
        UpdateOrder.upStatus(id_item,'ED')
        # Add note
        NotesAdd.addNote(order,f'{iccid} com erro na Telcon. Verificar erro.')
        error = 'errorApiResult'
        return error
            
    for order in orders_all:
        
        order = Orders.objects.get(pk=order.id)
        order_id = order.order_id
        id_item = order.id
        iccid = order.id_sim.sim
        dataDay = order.data_day
        
        global endpointId
        endpointId = None
        global simStatus
        simStatus = None
        
        # Get tokem de acesso a API
        try:
            tokenApi = ApiTC.get_token()
            time.sleep(2)
        except:
            errorAPI()
        ##
        
        conn = http.client.HTTPSConnection(settings.APITC_HTTPCONN)
        headers = ApiTC.get_headers(tokenApi)
        time.sleep(2)
        
        # Get EndPointID / Status
        try:
            get_iccid = ApiTC.get_iccid(iccid, headers)
            endpointId = get_iccid[0]
            simStatus = get_iccid[1]
            print('>>>>>>>>>> endpointId',endpointId)
            print('>>>>>>>>>> simStatus',simStatus)  
        except:            
            errorAPI()      
        ##

        # Variaveis globais
        global note
        global process
        note = ''
        process = False
        
        # Plan Change
        ApiTC.planChange(endpointId,headers,dataDay)
        NotesAdd.addNote(order,f'{iccid} Plano alterado para {dataDay}')    

        if simStatus == 'Pre-Active':
            # Ativar SIM na operadora
            payload = json.dumps({
                "Request": {
                    "endPointId": f"{endpointId}"
                }
            })
            conn.request("POST", "/api/EndPointActivation", payload, headers)
            # Add note
            note = f'{iccid} ativado com sucesso na Telcon'
            
            process = True
            
        else:
            # Alterar SIM na operadora
            if simStatus == 'Active':
                print('simStatus == Active')
                # Add note
                NotesAdd.addNote(order,f'{iccid} já estava ativado na Telcon')
                # Change Status
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
                # Add note
                note = f'{iccid} reativado com sucesso na Telcon'
                
                process = True
                
            else:
                print('simStatus == Other')
                # Change Status
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
            except:
                resultCode = None
                resultDescription = None
            
            print('>>>>>>>>>> resultCode', resultCode)
            print('>>>>>>>>>> resultDescription', resultDescription)
            
            if resultCode == 0:
                # Change Status
                UpdateOrder.upStatus(id_item,'AT')
                StatusStore.upStatus(order_id,'ativado')
                # Add note
                NotesAdd.addNote(order,f'{note} TC: {resultDescription}')
            else:
                # Change Status
                UpdateOrder.upStatus(id_item,'EA')
                # Add note
                NotesAdd.addNote(order,f'TC: {resultDescription}')
                
    print('>>>>>>>>>> ATIVAÇÂO FINALIZADA')

@shared_task
def simDeactivateTC(id=None):
    
    if id is not None:
        print(f'O id fornecido é {id}')
    else:
        print('Nenhum id fornecido')
        
    # Timezone /Today
    london_tz = pytz.timezone('Europe/London')
    today = pd.Timestamp.now(tz=london_tz).date()
    
    # Select Orders
    if id == None:
        print('>>>>>>>>>> desativer SEM ID')
        orders_all = Orders.objects.filter(order_status='AT', id_sim__operator='TC')
    else:
        print('>>>>>>>>>> desativer com ID')
        orders_all = Orders.objects.filter(pk=id)
    
    # Verificar se há pedidos para desativar
    if not orders_all:
        print('>>>>>>>>>> Nenhum pedido para desativar')
        return
    print('>>>>>>>>>> orders_all',orders_all)
    
    fields_df = ['id', 'order_id', 'id_sim__sim', 'days', 'activation_date']
    orders_df = pd.DataFrame((orders_all.values(*fields_df)))
    print('>>>>>>>>>> orders_df 1',orders_df)
    # orders_df['id'] = pd.to_numeric(orders_df['id'])
    orders_df['activation_date'] = pd.to_datetime(orders_df['activation_date'])
    orders_df['return_date'] = orders_df['activation_date'] + pd.to_timedelta(orders_df['days'], unit='d') - pd.to_timedelta(1, unit='d')
    # orders_df['return_date'] = pd.to_datetime(orders_df['return_date'])
    if id == None:
        orders_df = orders_df[orders_df['return_date'] == today]

    print('>>>>>>>>>> orders_df 2',orders_df)
    print('>>>>>>>>>> DESATIVAÇÂO INICIADA')
    
    for index, ord in orders_df.iterrows():
        order = Orders.objects.get(pk=ord['id'])
        order_id = ord['order_id']
        ord['order_id']
        id_item = ord['id']
        iccid = ord['id_sim__sim']
        
        global note
        note = ''
        global resultCode
        resultCode = None
        global resultDescription
        resultDescription = None        
        global endpointId
        endpointId = None
        global simStatus
        simStatus = None
        
        def errorAPI():
            print('>>>>>>>>>> ERRO API')
            # Change Status
            UpdateOrder.upStatus(id_item,'ED')
            # Add note
            NotesAdd.addNote(order,f'{iccid} com erro na Telcon. Verificar erro.')
            error = 'errorApiResult'
            return error
        
        # Get tokem de acesso a API
        try:
            tokenApi = ApiTC.get_token()
            time.sleep(2)
        except:
            errorAPI()
        ##
        conn = http.client.HTTPSConnection(settings.APITC_HTTPCONN)
        headers = ApiTC.get_headers(tokenApi)
        time.sleep(2)
         
        # Get EndPointID / Status
        try:
            get_iccid = ApiTC.get_iccid(iccid, headers)
            endpointId = get_iccid[0]
            simStatus = get_iccid[1]
            print('>>>>>>>>>> endpointId',endpointId)
            print('>>>>>>>>>> simStatus',simStatus)  
        except:            
            errorAPI()
      
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
        # Add note
            
        res = conn.getresponse()
        data = json.loads(res.read())
        try:
            resultCode = int(data["Response"]["resultCode"])
            resultDescription = data["Response"]["resultParam"]["resultDescription"]
        except:
            resultCode = None
            resultDescription = None

        print('>>>>>>>>>> resultCode', resultCode)
        print('>>>>>>>>>> resultDescription', resultDescription)
        
        if resultCode == 0:
            print('>>>>>>>>>> DESATIVADO')
            print('>>>>>>>>>> id', id)
            if id == None:
                print('>>>>>>>>>> Change Status')                
                # Change Status                
                UpdateOrder.upStatus(id_item,'CN')
                StatusStore.upStatus(order_id,'completed')
                sim_put = Sims.objects.get(pk=order.id_sim.id)
                sim_put.sim_status = 'DE'
                sim_put.save()
            # Add note
            NotesAdd.addNote(order,f'{iccid} desativado com sucesso na Telcon. TC: {resultDescription}')
        else:
            print('>>>>>>>>>> ERRO DESATIVADO')
            if id == None:
                # Change Status
                UpdateOrder.upStatus(id_item,'ED')
            # Add note
            NotesAdd.addNote(order,f'{iccid} com erro na Telcon. Verificar erro. TC: {resultDescription}')
                
    print('>>>>>>>>>> DESATIVAÇÂO FINALIZADA')


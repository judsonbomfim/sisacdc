from celery import shared_task
import os
from apps.orders.models import Orders, Notes
from apps.orders.views import ApiStore, StatusSis
from apps.send_email.tasks import send_email_sims
from apps.sims.models import Sims
from datetime import datetime, timedelta

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
            # ALteração provisória
            now = datetime.now().date()
            date_2_days = now + timedelta(days=2)
            if ord.activation_date > date_2_days:
                operator_i = 'TC'
            else: operator_i = 'CM'
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
                addNote(f'Não há estoque de {operator_i} - {type_sim_i} no sistema')      
                msg_error.append(f'Não há estoque de {operator_i} - {type_sim_i} no sistema')
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
        
        addNote(f'(e)SIM adicionado')
        
        status_sis_site = StatusSis.st_sis_site()
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
from celery import shared_task
import os
from apps.orders.models import Orders
from apps.orders.views import ApiStore, StatusSis
from apps.sims.models import Sims

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

        # Escolher operadora
        # if product_i == 'chip-internacional-europa' and countries_i == False and type_sim_i == 'esim':
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
            msg_error.append(f'Não há estoque de {operator_i} - {type_sim_i} no sistema')
            continue
        
        # update order
        # Save SIMs
        # if sim_ds.type_sim == 'esim':
        #     status_ord = 'EE'
        # else: status_ord = 'ES'
        status_ord = 'EE'
        
        order_put = Orders.objects.get(pk=id_id_i)
        order_put.id_sim_id = sim_ds.id            
        order_put.order_status = status_ord
        order_put.save()
        
        # update sim
        sim_put = Sims.objects.get(pk=sim_ds.id)
        sim_put.sim_status = 'AT'
        sim_put.save()           
        
        status_sis_site = StatusSis.st_sis_site()
                
        if status_ord in status_sis_site:
            update_store = {
                'status': status_sis_site[status_ord]
            }
        # Enviar eSIM para site
        if sim_put.type_sim == 'esim':
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
    

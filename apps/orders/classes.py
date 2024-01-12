from woocommerce import API
import os
from apps.orders.models import Orders, Notes

# Conect woocommerce api
class ApiStore():
    @staticmethod
    def conectApiStore():
        wcapi = API(
            url = str(os.getenv('url_site')),
            consumer_key = str(os.getenv('consumer_key')),
            consumer_secret = str(os.getenv('consumer_secret')),
            wp_api = True,
            version = 'wc/v3',
            timeout = 5000
        )
        return wcapi

    @staticmethod
    def updateEsimStore(order_id):    
        url_painel = str(os.getenv('URL_PAINEL'))
        esims_order = Orders.objects.filter(order_id=order_id).filter(id_sim__link__isnull=False)
        esims_list = ''
        update_store = {"meta_data":[{"key": "campo_esims","value": ''}]}
        if esims_order:
            for esims_o in esims_order:
                link_sim = esims_o.id_sim.link              
                esims_list = esims_list + f"<img src='{url_painel}{link_sim}' style='width: 300px; margin:40px;'>"
                update_store = {
                    "meta_data": [
                        {
                            "key": "campo_esims",
                            "value": esims_list
                        }
                    ]
                }
        else:
            pass
        # Conect Store
        apiStore = ApiStore.conectApiStore()
        apiStore.put(f'orders/{order_id}', update_store).json() 

class StatusSis():
    @staticmethod
    def st_sis_site():
        status_sis_site = {
            'AE': 'agd-envio',
            'AS': 'em-separacao',
            'AA': 'agd-ativacao',        
            'CC': 'cancelled',
            'ES': 'em-separacao',
            'MB': 'motoboy',
            'RS': 'reuso',
            'RT': 'retirada',
            'RE': 'reembolsar',
            'CN': 'completed',        
        }
        return status_sis_site

class DateFormats():
    # Date - 2023-05-16T18:40:27
    @staticmethod
    def dateHour(dh):
        date = dh[0:10]
        hour = dh[11:19]
        date_hour = f'{date} {hour}'
        return date_hour
    # Date - 17/06/2023
    @staticmethod
    def dateF(d):
        dia = d[0:2]
        mes = d[3:5]
        ano = d[6:10]
        dataForm = f'{ano}-{mes}-{dia}'
        return dataForm
    # Date - 2023-05-17 00:56:18+00:00 > 00/00/00
    @staticmethod
    def dateDMA(dma):
        ano = dma[2:4]
        mes = dma[5:7]
        dia = dma[8:10]
        data_dma = f'{dia}/{mes}/{ano}'
        return data_dma
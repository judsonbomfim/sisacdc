from woocommerce import API
import os
from apps.orders.models import Orders, Notes
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

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

class StatusStore():
    @staticmethod
    def st_sis_site():
        status_sis_site = {
            'AA': 'wc-agd-ativacao',  # ← Adicionar 'wc-'
            'AE': 'wc-agd-envio',
            'AG': 'wc-agencia',
            'AS': 'wc-em-andamento',
            'AI': 'wc-em-andamento',
            'AT': 'wc-ativado',
            'CC': 'cancelled',
            'CN': 'wc-completed', 
            'DE': 'wc-desativado', 
            'DA': 'wc-data-em-aberto',
            'DS': 'wc-desativado', 
            'EI': 'wc-em-andamento',
            'EE': 'wc-em-andamento',
            'ES': 'wc-em-separacao',
            'MB': 'wc-motoboy',
            'PV': 'wc-agd-ativacao',
            'RE': 'wc-reembolsar',
            'RB': 'wc-reembolsado',
            'RC': 'wc-reembolso-parcial',
            'RS': 'wc-reuso',
            'RT': 'wc-retirada',
        }
        return status_sis_site

class UpdateStore():
    @staticmethod
    def upStore(order_id=None, item_id_store=None, _data_ativacao=None, _sim=None, 
                _qrcode=None, _status=None, status_g=None):
        
        logger.info(f">>>>>>>>>> UpdateStore.upStore INICIADO - Pedido: {order_id}")
        logger.info(f"  - item_id_store: {item_id_store}")
        logger.info(f"  - _status: {_status}")
        logger.info(f"  - status_g: {status_g}")
        
        apiStore = ApiStore.conectApiStore()
        
        meta_data = []
        update_store = {}
        
        # Preparar meta_data para item específico
        if item_id_store is not None:
            logger.info(f"  - Preparando meta_data para item {item_id_store}")
            
            if _data_ativacao:
                meta_data.append({"key": "_data_ativacao", "value": _data_ativacao})
            if _sim:
                meta_data.append({"key": "_sim", "value": _sim})
            if _qrcode:
                meta_data.append({"key": "_qrcode", "value": _qrcode if _qrcode else ""})
            if _status:
                status_sis_site = StatusStore.st_sis_site()
                if _status in status_sis_site:
                    meta_data.append({"key": "_status", "value": status_sis_site[_status]})
                    logger.info(f"  - Status mapeado: {_status} -> {status_sis_site[_status]}")
                else:
                    logger.warning(f"  - Status '{_status}' NÃO encontrado no mapeamento!")
            
            update_store = {
                'line_items': [{
                    "id": int(item_id_store),
                    "meta_data": meta_data
                }]
            }
            logger.info(f"  - Meta_data preparado: {meta_data}")

        # Preparar status geral
        if status_g is not None:
            status_sis_site = StatusStore.st_sis_site()
            if status_g in status_sis_site:
                update_store['status'] = status_sis_site[status_g]
                logger.info(f"  - Status geral: {status_g} -> {status_sis_site[status_g]}")
            else:
                logger.warning(f"  - Status geral '{status_g}' NÃO encontrado no mapeamento!")
        
        logger.info(f"  - Dados finais para WooCommerce: {update_store}")
        
        # Fazer a requisição
        if update_store:
            try:
                response = apiStore.put(f'orders/{order_id}', update_store)
                
                logger.info(f">>>>>>>>>> Resposta WooCommerce - Pedido {order_id}:")
                logger.info(f"  - Status HTTP: {response.status_code}")
                logger.info(f"  - Headers: {dict(response.headers)}")
                logger.info(f"  - Resposta: {response.text}")
                
                if response.status_code in [200, 201]:
                    logger.info(f">>>>>>>>>> Pedido {order_id} atualizado com SUCESSO")
                    return True
                else:
                    logger.error(f">>>>>>>>>> ERRO na atualização - Pedido {order_id}")
                    logger.error(f"  - Status: {response.status_code}")
                    logger.error(f"  - Resposta completa: {response.text}")
                    return False
                    
            except Exception as e:
                logger.exception(f">>>>>>>>>> EXCEÇÃO ao atualizar pedido {order_id}: {e}")
                return False
        else:
            logger.warning(f">>>>>>>>>> NADA para atualizar - Pedido {order_id}")
            return False

    @staticmethod
    def check_available_status():
        """Verificar status disponíveis no WooCommerce"""
        apiStore = ApiStore.conectApiStore()
        try:
            # Buscar status do sistema
            response = apiStore.get('system_status')
            logger.info(f"System Status: {response.json()}")
            
            # Buscar um pedido para ver status possíveis
            response_orders = apiStore.get('orders', params={'per_page': 1})
            orders = response_orders.json()
            if orders:
                logger.info(f"Status de exemplo em pedido: {orders[0].get('status')}")
                
            return response.json(), orders
            
        except Exception as e:
            logger.exception(f"Erro ao verificar status: {e}")
            return None, None

class NoteStore():
    @staticmethod
    def addNoteStore(order_id,note,user_name='Sistema'):
        order_id = order_id
        note = note
        user_name = user_name
        apiStore = ApiStore.conectApiStore()
        note_i = f'{user_name} - {note}'        
        add_note = {
            "note": note_i
        }
        apiStore.post(f'orders/{order_id}/notes', add_note).json()        

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

class NotesAdd():
    @staticmethod
    def addNote(id_item,note,id_user=None,type_note='S'):
        add_sim = Notes( 
            id_item = id_item,
            id_user = id_user,
            note = note,
            type_note = type_note,
        )
        add_sim.save()

class UpdateOrder():
    @staticmethod
    def upStatus(order_id,order_st):
        order = Orders.objects.get(pk=order_id)
        order.order_status = order_st
        order.save()
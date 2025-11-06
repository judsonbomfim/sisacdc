from woocommerce import API
import os
from apps.orders.models import Orders, Notes
from django.contrib.auth.models import User

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
            'AA': 'agd-ativacao',
            'AE': 'agd-envio',
            'AG': 'agencia',
            'AS': 'em-andamento',
            'AI': 'em-andamento',
            'AT': 'ativado',
            'CC': 'cancelled',
            'CN': 'completed', 
            'DE': 'desativado', 
            'DA': 'data-em-aberto',
            'DS': 'desativado', 
            'EI': 'em-andamento',
            'EE': 'em-andamento',
            'ES': 'em-separacao',
            'MB': 'motoboy',
            'PV': 'agd-ativacao',
            'RE': 'reembolsar',
            'RB': 'reembolsado',
            'RC': 'reembolso-parcial',
            'RS': 'reuso',
            'RT': 'retirada',
        }
        return status_sis_site

class UpdateStore():
    @staticmethod
    def upStore(order_id, item_id_store=None, _data_ativacao=None, _sim=None, _qrcode=None, _status=None,status_g=None):
        meta_data = []
        update_store = {}
        if item_id_store != None:
            if _data_ativacao:
                meta_data.append({
                    "key": "_data_ativacao",
                    "value": _data_ativacao,
                })
            if _sim:
                meta_data.append({
                    "key": "_sim",
                    "value": _sim,
                })
            if _qrcode:
                meta_data.append({
                    "key": "_qrcode",
                    "value": _qrcode if _qrcode else "",
                })
            if _status:
                # listaStatus = dict(Orders.order_status.field.choices)
                status_sis_site = StatusStore.st_sis_site()
                meta_data.append({
                    "key": "_status",
                    "value": status_sis_site[_status],
                })
            update_store = {
                'line_items': [
                    {
                        "id": int(item_id_store),
                        "meta_data": meta_data
                    }
                ]}
        if status_g or _status:
            print(f">>>>>>>>>> Status {_status} / {status_g}")
            status_sis_site = StatusStore.st_sis_site()
            print(f">>>>>>>>>> Atualizando status geral para {status_sis_site[status_g]} no site - Pedido: {order_id}")
            update_store['status'] = status_sis_site[_status]
            update_store['status'] = status_sis_site[status_g]
        if update_store:
            apiStore = ApiStore.conectApiStore()
            try:
                apiStore.put(f'orders/{order_id}', update_store)
                print(f">>>>>>>>>> Pedido {order_id} atualizado no site com sucesso.")
            except Exception as e:
                print(f">>>>>>>>>> ERRO ao atualizar pedido {order_id} no site: {e}")
            # Tentar atualizar o pedido novamente
            apiStore.put(f'orders/{order_id}', update_store)

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
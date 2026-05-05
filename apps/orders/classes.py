"""
Classes de integração do app **orders** com o WooCommerce (API Store).

Fornece acesso à API REST do WooCommerce para importação de pedidos,
atualização de status e metadados, e registro de notas nos pedidos.

Classes:
    - :class:`ApiStore` — Conexão com a API WooCommerce.
    - :class:`StatusStore` — Mapeamento de status interno → status da loja.
    - :class:`UpdateStore` — Atualização de pedidos na loja.
    - :class:`NoteStore` — Registro de notas nos pedidos da loja.
    - :class:`DateFormats` — Utilitários de formatação de datas.
    - :class:`NotesAdd` — Registro de notas internas no banco.
    - :class:`UpdateOrder` — Atualização de status no banco local.
"""

from woocommerce import API
import os
from apps.orders.models import Orders, Notes
from django.contrib.auth.models import User
import logging
logger = logging.getLogger(__name__)

class ApiStore():
    """Fábrica de conexão autenticada com a API REST do WooCommerce (wc/v3)."""

    @staticmethod
    def conectApiStore():
        """
        Cria e retorna uma instância da API WooCommerce configurada.

        Lê as credenciais das variáveis de ambiente ``url_site``,
        ``consumer_key`` e ``consumer_secret``.

        Returns:
            woocommerce.API: Instância da API pronta para uso.
        """
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
    """Mapeia os códigos de status internos para os slugs de status da loja WooCommerce."""

    @staticmethod
    def st_sis_site():
        """
        Retorna o dicionário de mapeamento: código SISACDC → slug WooCommerce.

        Returns:
            dict: Mapeamento de status, ex: ``{'AT': 'ativado', 'CC': 'cancelled', ...}``
        """
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
    """Atualiza pedidos e metadados de itens diretamente na loja WooCommerce via API."""

    @staticmethod
    def upStore(order_id=None, item_id_store=None, _data_ativacao=None, _sim=None,
                _qrcode=None, _status=None, status_g=None):
        """
        Envia atualização de metadados e/ou status de um pedido para a loja.

        Args:
            order_id (int): ID do pedido no WooCommerce.
            item_id_store (str): ID do item dentro do pedido (para atualizar metadados).
            _data_ativacao (str): Data de ativação formatada (meta ``_data_ativacao``).
            _sim (str): ICCID do SIM ativado (meta ``_sim``).
            _qrcode (str): URL do QR code do eSIM (meta ``_qrcode``).
            _status (str): Código de status interno a ser convertido e aplicado ao item.
            status_g (str): Código de status para atualizar o status geral do pedido.

        Returns:
            bool: ``True`` se a atualização foi bem-sucedida (HTTP 200/201), ``False`` caso contrário.
        """
        
        apiStore = ApiStore.conectApiStore()
        
        meta_data = []
        update_store = {}
        
        # Preparar meta_data para item específico
        if item_id_store is not None:            
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
            
            update_store = {
                'line_items': [{
                    "id": int(item_id_store),
                    "meta_data": meta_data
                }]
            }

        # Preparar status geral
        if status_g is not None:
            status_sis_site = StatusStore.st_sis_site()
            if status_g in status_sis_site:
                update_store['status'] = status_sis_site[status_g]
        
        # Fazer a requisição
        if update_store:
            try:
                response = apiStore.put(f'orders/{order_id}', update_store)
                if response.status_code in [200, 201]:
                    return True
                else:
                    return False                    
            except Exception as e:
                logger.error(f"Erro ao atualizar pedido {order_id} na loja: {e}")
                return False        

class NoteStore():
    """Registra notas nos pedidos do WooCommerce via API."""

    @staticmethod
    def addNoteStore(order_id, note, user_name='Sistema'):
        """
        Adiciona uma nota ao pedido na loja.

        Args:
            order_id (int): ID do pedido no WooCommerce.
            note (str): Conteúdo da nota.
            user_name (str): Nome exibido como autor da nota. Padrão: ``'Sistema'``.
        """
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
    """Utilitários para conversão e formatação de datas usadas na importação de pedidos."""

    # Date - 2023-05-16T18:40:27
    @staticmethod
    def dateHour(dh):
        """
        Extrai data e hora de uma string ISO 8601.

        Args:
            dh (str): String no formato ``'2023-05-16T18:40:27'``.

        Returns:
            str: String no formato ``'2023-05-16 18:40:27'``.
        """
        date = dh[0:10]
        hour = dh[11:19]
        date_hour = f'{date} {hour}'
        return date_hour
    # Date - 17/06/2023
    @staticmethod
    def dateF(d):
        """
        Converte data no formato ``DD/MM/YYYY`` para ``YYYY-MM-DD`` (ISO 8601).

        Args:
            d (str): Data no formato ``'17/06/2023'``.

        Returns:
            str: Data no formato ``'2023-06-17'``.
        """
        dia = d[0:2]
        mes = d[3:5]
        ano = d[6:10]
        dataForm = f'{ano}-{mes}-{dia}'
        return dataForm
    # Date - 2023-05-17 00:56:18+00:00 > 00/00/00
    @staticmethod
    def dateDMA(dma):
        """
        Converte datetime do banco de dados para formato ``DD/MM/AA``.

        Args:
            dma (str): Datetime no formato ``'2023-05-17 00:56:18+00:00'``.

        Returns:
            str: Data no formato ``'17/05/23'``.
        """
        ano = dma[2:4]
        mes = dma[5:7]
        dia = dma[8:10]
        data_dma = f'{dia}/{mes}/{ano}'
        return data_dma

class NotesAdd():
    """Adiciona notas internas (banco local) associadas a pedidos."""

    @staticmethod
    def addNote(id_item, note, id_user=None, type_note='S'):
        """
        Cria e persiste uma nota no banco de dados.

        Args:
            id_item (Orders): Instância do pedido ao qual a nota será associada.
            note (str): Texto da nota.
            id_user (User, optional): Usuário autor. Nulo para notas do sistema.
            type_note (str): Tipo — ``'S'`` (Sistema) ou ``'P'`` (Privada). Padrão: ``'S'``.
        """
        add_sim = Notes( 
            id_item = id_item,
            id_user = id_user,
            note = note,
            type_note = type_note,
        )
        add_sim.save()

class UpdateOrder():
    """Atualiza o status de pedidos no banco de dados local."""

    @staticmethod
    def upStatus(order_id, order_st):
        """
        Altera o ``order_status`` de um pedido pelo PK.

        Args:
            order_id (int): PK do pedido em ``Orders``.
            order_st (str): Novo código de status (ver choices ``ORDER_STATUS``).
        """
        order = Orders.objects.get(pk=order_id)
        order.order_status = order_st
        order.save()
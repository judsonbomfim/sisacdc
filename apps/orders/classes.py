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
    - :class:`ExportClients` — Exportação de clientes WooCommerce para CSV.
"""

import csv
import json
import logging
import os
import uuid
from datetime import date

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse
from woocommerce import API

from apps.orders.models import Orders, Notes

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


class ExportClients:
    """Exportação paginada de clientes do WooCommerce com acompanhamento de progresso."""

    CSV_HEADER = ['Nome', 'Sobrenome', 'Billing phone', 'Billing cellphone', 'Email']
    PER_PAGE = 100

    @classmethod
    def export_dir(cls):
        export_dir = os.path.join(settings.BASE_DIR, 'tmp', 'exports')
        os.makedirs(export_dir, exist_ok=True)
        return export_dir

    @classmethod
    def progress_path(cls, export_id):
        return os.path.join(cls.export_dir(), f'{export_id}_progress.json')

    @classmethod
    def csv_path(cls, export_id):
        return os.path.join(cls.export_dir(), f'{export_id}.csv')

    @classmethod
    def write_progress(cls, export_id, data):
        with open(cls.progress_path(export_id), 'w', encoding='utf-8') as progress_file:
            json.dump(data, progress_file, ensure_ascii=False)

    @classmethod
    def read_progress(cls, export_id):
        progress_path = cls.progress_path(export_id)
        if not os.path.exists(progress_path):
            return {
                'status': 'pending',
                'message': 'Iniciando exportação...',
                'processed': 0,
                'total': 0,
                'page': 0,
                'total_pages': 0,
            }
        with open(progress_path, encoding='utf-8') as progress_file:
            return json.load(progress_file)

    @staticmethod
    def _cellphone(customer):
        billing = customer.get('billing') or {}
        cellphone = billing.get('cellphone', '')
        if cellphone:
            return cellphone
        for meta in customer.get('meta_data') or []:
            if meta.get('key') in ('billing_cellphone', 'cellphone', '_billing_cellphone'):
                return meta.get('value', '') or ''
        return ''

    @staticmethod
    def _customer_row(customer):
        billing = customer.get('billing') or {}
        return [
            billing.get('first_name') or customer.get('first_name', ''),
            billing.get('last_name') or customer.get('last_name', ''),
            billing.get('phone', ''),
            ExportClients._cellphone(customer),
            billing.get('email') or customer.get('email', ''),
        ]

    @classmethod
    def process_next_page(cls, export_id):
        progress_path = cls.progress_path(export_id)
        if not os.path.exists(progress_path):
            return {'status': 'error', 'message': 'Exportação não encontrada.'}

        with open(progress_path, encoding='utf-8') as progress_file:
            state = json.load(progress_file)

        if state.get('status') in ('done', 'error'):
            return state

        csv_path = cls.csv_path(export_id)
        page = 1 if state.get('status') == 'pending' else state.get('page', 0) + 1

        try:
            if state.get('status') == 'pending':
                with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csv_file:
                    csv.writer(csv_file).writerow(cls.CSV_HEADER)

            api_store = ApiStore.conectApiStore()
            response = api_store.get('customers', params={
                'per_page': cls.PER_PAGE,
                'page': page,
                'orderby': 'id',
                'order': 'asc',
            })

            if response.status_code >= 500:
                raise RuntimeError(f'Erro no servidor da loja: HTTP {response.status_code}')
            if response.status_code >= 400:
                raise RuntimeError(f'Erro ao buscar clientes: HTTP {response.status_code}')

            total_pages = int(response.headers.get('X-WP-TotalPages', 1) or 1)
            total_customers = int(response.headers.get('X-WP-Total', 0) or 0)
            customers = response.json() or []

            with open(csv_path, 'a', newline='', encoding='utf-8-sig') as csv_file:
                writer = csv.writer(csv_file)
                for customer in customers:
                    writer.writerow(cls._customer_row(customer))

            processed = state.get('processed', 0) + len(customers)
            done = page >= total_pages or not customers

            new_state = {
                'status': 'done' if done else 'running',
                'page': page,
                'total_pages': total_pages,
                'processed': processed,
                'total': total_customers,
                'message': (
                    f'Exportação concluída — {processed} clientes'
                    if done else
                    f'Página {page} de {total_pages} — {processed} clientes exportados'
                ),
            }
            cls.write_progress(export_id, new_state)
            if done:
                logger.info(f'[ExportClients] Exportação {export_id} concluída: {processed} clientes')
            return new_state

        except Exception as exc:
            logger.error(f'[ExportClients] Falha na exportação {export_id}: {exc}')
            error_state = {
                'status': 'error',
                'processed': state.get('processed', 0),
                'total': state.get('total', 0),
                'message': f'Erro na exportação: {exc}',
            }
            cls.write_progress(export_id, error_state)
            return error_state

    @classmethod
    def start(cls):
        export_id = str(uuid.uuid4())
        cls.export_dir()
        cls.write_progress(export_id, {
            'status': 'pending',
            'page': 0,
            'total_pages': 0,
            'processed': 0,
            'total': 0,
            'message': 'Iniciando exportação...',
        })
        return export_id

    @classmethod
    def build_download_response(cls, export_id):
        csv_path = cls.csv_path(export_id)
        if not os.path.exists(csv_path):
            return None
        with open(csv_path, 'rb') as csv_file:
            response = HttpResponse(csv_file.read(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="clientes-{date.today()}.csv"'
        return response

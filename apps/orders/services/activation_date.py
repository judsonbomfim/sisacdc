import logging
from dataclasses import dataclass
from datetime import datetime

from django.db import transaction

from apps.orders.classes import DateFormats, NotesAdd
from apps.orders.models import Orders
from apps.voice_calls.models import VoiceCalls

logger = logging.getLogger(__name__)


class OrderNotFoundError(Exception):
    """Pedido local não encontrado para order_id + item_id da loja."""


class IccidMismatchError(Exception):
    """ICCID informado não corresponde ao SIM do pedido."""


@dataclass
class ActivationDateApplyResult:
    updated: bool
    order_pk: int
    activation_date: str


def _parse_ymd(value: str):
    return datetime.strptime(value, '%Y-%m-%d').date()


def _find_order(payload: dict) -> Orders:
    order_id = payload['order_id']
    item_id_store = str(payload['item_id'])
    iccid = (payload.get('iccid') or '').strip()

    qs = Orders.objects.select_for_update().filter(
        order_id=order_id,
        item_id_store=item_id_store,
    )
    order = qs.first()
    if order is None and iccid:
        order = (
            Orders.objects.select_for_update()
            .filter(order_id=order_id, id_sim__sim=iccid)
            .first()
        )
    if order is None:
        raise OrderNotFoundError(
            f'Pedido não encontrado (order_id={order_id}, item_id={item_id_store}).'
        )

    if iccid and order.id_sim_id and order.id_sim.sim != iccid:
        raise IccidMismatchError(
            f'ICCID não confere com o pedido (order_id={order_id}, item_id={item_id_store}).'
        )

    return order


@transaction.atomic
def apply_activation_date_from_store(payload: dict) -> ActivationDateApplyResult:
    """
    Aplica ``data_nova`` no pedido local após alteração na loja WooCommerce.

    Não reenvia dados para a loja (evita loop).
    """
    new_date = _parse_ymd(payload['data_nova'])
    order = _find_order(payload)

    if order.activation_date == new_date:
        logger.info(
            'Webhook data-ativacao idempotente order_id=%s item_id=%s data=%s',
            payload['order_id'],
            payload['item_id'],
            new_date.isoformat(),
        )
        return ActivationDateApplyResult(
            updated=False,
            order_pk=order.pk,
            activation_date=new_date.isoformat(),
        )

    old_date = order.activation_date
    order.activation_date = new_date

    if order.order_status in ('EI', 'DA'):
        order.order_status = 'AS'

    order.save()

    if order.calls:
        voice = VoiceCalls.objects.filter(id_item=order.pk).first()
        if voice:
            voice.activation_date = new_date
            voice.save()

    note_old = DateFormats.dateDMA(str(old_date))
    note_new = DateFormats.dateDMA(str(new_date))
    origem = payload.get('origem') or 'cliente'
    NotesAdd.addNote(
        id_item=order,
        note=f'Data alterada de {note_old} para {note_new} (origem: {origem} / WooCommerce)',
        id_user=None,
        type_note='S',
    )

    logger.info(
        'Webhook data-ativacao aplicado order_id=%s item_id=%s de=%s para=%s order_pk=%s',
        payload['order_id'],
        payload['item_id'],
        old_date.isoformat(),
        new_date.isoformat(),
        order.pk,
    )

    return ActivationDateApplyResult(
        updated=True,
        order_pk=order.pk,
        activation_date=new_date.isoformat(),
    )

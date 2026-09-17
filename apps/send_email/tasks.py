"""
Tarefas Celery do app **send_email**.

Envia notificações HTML por e-mail para clientes após ativação de SIM ou voz.
"""

from urllib import request
from celery import shared_task
from django.shortcuts import redirect
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from apps.orders.models import Orders, Notes, User
from apps.orders.classes import ApiStore, StatusStore, UpdateStore
from apps.voice_calls.models import VoiceCalls
from apps.voice_calls.classes import NumberFormatter
import time

import logging
logger = logging.getLogger(__name__)

@shared_task
def send_email_sims(id=None, troca=None, data_alterada=None):
    """
    Envia e-mail de ativação/desativação de SIM para o cliente.

    Seleciona pedidos com status ``EE`` (Enviar E-mail) ou um pedido específico
    pelo PK. Renderiza template HTML, envia via SMTP e, se o pedido estava em
    ``EE``, atualiza para ``AA`` (Agd. Ativação) para não reenviar.

    Args:
        id (int, optional): PK do pedido. Se ``None``, processa todos os pedidos
            com status ``EE``.
        troca (bool, optional): E-mail de troca de chip.
        data_alterada (bool, optional): E-mail de alteração da data de ativação.
    """
    orders_all = None
    if id == None:
        orders_all = Orders.objects.filter(order_status='EE')
    else:
        orders_all = Orders.objects.filter(pk=id)
        if not orders_all.exists():
            logger.error(f'Pedido pk={id} não encontrado para envio de e-mail!')
            return None
        logger.info(f'Enviando e-mail para o pedido pk={id}...')
        
    url_site = settings.URL_CDN
    url_img = f'{url_site}/email/'

    
    for order in orders_all:
        id = order.id
        name = order.client if order.client else None
        client_email = order.email if order.email else None
        order_id = order.item_id if order.item_id else None
        ord_id = order.order_id if order.order_id else None
        order_st = order.order_status if order.order_status else None
        qrcode = order.id_sim.link if order.id_sim else None
        activation_date = order.activation_date if order.activation_date else None
        operator = order.id_sim.operator if order.id_sim else None
        product = f'{order.get_product_display()} {order.get_data_day_display() if operator != "OR" else ""}'
        days = order.days if order.days else None
        product_plan = order.get_product_display() if order.get_product_display() else None
        product_s = order.product if order.product else None
        type_sim = order.id_sim.type_sim if order.id_sim else None
        sim = order.id_sim.sim if order.id_sim else None
        lpa = order.id_sim.lpa if order.id_sim and order.id_sim.lpa else ''
        countries = order.countries if order.countries else None
        link_esim_android = settings.LINK_ESIM_ANDROID
        link_esim_ios = settings.LINK_ESIM_IOS
        
        if (countries == True and product_s == 'chip-internacional-global') or product_s == 'chip-internacional-asia':
            hong_kong = True
        else:
            hong_kong = False
        
        context = {
            'url_site': url_site,
            'url_img': url_img,
            'name': name,
            'order_id': order_id,
            'order_st': order_st,
            'qrcode': qrcode,
            'activation_date': activation_date,
            'operator': operator,
            'product': product,
            'days': days,
            'product_plan': product_plan,
            'product_s': product_s,
            'type_sim': type_sim,
            'sim': sim,
            'lpa': lpa,
            'countries': countries,
            'link_esim_android': link_esim_android,
            'link_esim_ios': link_esim_ios,
            'hong_kong': hong_kong,
            'troca': bool(troca),
            'data_alterada': bool(data_alterada),
        }

        claimed_from_ee = False
        if order_st == 'EE':
            claimed_from_ee = (
                Orders.objects.filter(pk=order.pk, order_status='EE').update(order_status='AA') == 1
            )
            if not claimed_from_ee:
                logger.info(
                    'Pedido pk=%s já saiu de EE, e-mail duplicado ignorado',
                    order.pk,
                )
                continue
            order_st = 'AA'
            order.order_status = 'AA'

        try:
            html_content = render_to_string('painel/emails/send_email.html', context)
            text_content = strip_tags(html_content)
            if troca == True:
                subject = f"ATENÇÃO! Alteração de Chip do PEDIDO #{order_id}"
            elif data_alterada:
                subject = f"Alteração da data de ativação PEDIDO #{order_id}"
            elif type_sim == 'esim':
                subject = f"Entrega do eSIM PEDIDO #{order_id}"
            else:
                subject = f"Informações PEDIDO #{order_id}"
            email = EmailMultiAlternatives(
                #subject
                subject,
                #content
                text_content,
                #from email
                settings.DEFAULT_FROM_EMAIL,
                #to
                [client_email],
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
        except Exception as e:
            logger.error(f'Erro ao enviar e-mail para o pedido {id}: {e}')
            if claimed_from_ee:
                Orders.objects.filter(pk=order.pk, order_status='AA').update(order_status='EE')
            continue
        
        id_user = None
        type_note = 'S'
            
        # Add note
        if data_alterada:
            email_note = 'E-mail de alteração de data enviado com sucesso!'
        else:
            email_note = 'E-mail enviado com sucesso!!'
        add_note = Notes( 
            id_item = order,
            id_user = id_user,
            note = email_note,
            type_note = type_note,
        )
        add_note.save()

        if claimed_from_ee:
            try:
                UpdateStore.upStore(
                    order_id=ord_id,
                    item_id_store=order.item_id_store if order.item_id_store else None,
                    _status='AA',
                    status_g='AA',
                )
            except Exception as e:
                logger.error(
                    'E-mail enviado, mas falhou ao sincronizar status AA na loja | pk=%s | erro=%s',
                    order.pk,
                    e,
                )


@shared_task
def send_email_voice(id=None):
    
    voice_all = None
    if id == None:
        voice_all = VoiceCalls.objects.filter(order_status='EE')
    else:
        voice_all = VoiceCalls.objects.filter(pk=id)
    
    url_site = settings.URL_CDN
    url_img = f'{url_site}/email/'
    
    for voice in voice_all:
        id_voice = voice.id
        order_id_id = voice.id_item.id
        order_id = voice.id_item.item_id
        order_st = voice.id_item.order_status
        name = voice.id_item.client
        email = voice.id_item.email
        try: qrcode = voice.id_number.number_qrcode
        except: qrcode = None
        activation_date = voice.id_item.activation_date
        product = 'Ativação do Plano Chamada de Voz'
        number = NumberFormatter.format(voice.id_number.number)
        days = voice.id_item.days
        
        context = {
            'url_site': url_site,
            'url_img': url_img,
            'id_voice': id_voice,
            'order_id': order_id,
            'name': name,
            'email': email,
            'qrcode': qrcode,
            'activation_date': activation_date,
            'product': product,
            'number': number,
            'days': days,     
        }
        
        # Send e-mail
        html_content = render_to_string('painel/emails/send_email_voice.html', context)
        text_content = strip_tags(html_content)
        subject = f"Chamada de Voz - #{order_id}"
        email = EmailMultiAlternatives(
            #subject
            subject,
            #content
            text_content,
            #from email
            settings.DEFAULT_FROM_EMAIL,
            #to
            [email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        if order_st == 'EE':
            # Update Voice
            voice_s = VoiceCalls.objects.get(pk=id_voice)
            voice_s.call_status = 'AA'
            voice_s.save()
        
        # Add note
        
        add_sim = Notes( 
            id_item = Orders.objects.get(pk=order_id_id),
            id_user = None,
            note = 'E-mail de Chamada de Voz enviado com sucesso!',
            type_note = 'S',
        )
        add_sim.save()
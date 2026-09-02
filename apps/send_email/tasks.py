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
def send_email_sims(id=None):
    """
    Envia e-mail de ativação/desativação de SIM para o cliente.

    Seleciona pedidos com status ``EE`` (Enviar E-mail) ou um pedido específico
    pelo PK. Renderiza template HTML, envia via SMTP e atualiza o status
    do pedido para ``CN`` (Conluído) após envio.

    Args:
        id (int, optional): PK do pedido. Se ``None``, processa todos os pedidos
            com status ``EE``.
    """
    orders_all = None
    if id == None:
        orders_all = Orders.objects.filter(order_status='EE')
    else:
        try:
            orders_all = Orders.objects.filter(pk=id)
            logger.info(f'Enviando e-mail para o pedido {id}...')
        except:
            logger.error(f'Pedido {id} não encontrado!')
            return None
        
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
        }        
        try:
            html_content = render_to_string('painel/emails/send_email.html', context)
            text_content = strip_tags(html_content)
            if type_sim == 'esim':
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
            continue
        
        # if order_st != 'CN' or order_st != 'AT':
        # ...
        
        id_user = None
        type_note = 'S'
            
        # Add note
        add_note = Notes( 
            id_item = order,
            id_user = id_user,
            note = 'E-mail enviado com sucesso!!',
            type_note = type_note,
        )
        add_note.save()


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
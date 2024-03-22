from celery import shared_task
from django.shortcuts import redirect
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from apps.orders.models import Orders, Notes
from apps.orders.classes import ApiStore, StatusSis
from apps.voice_calls.models import VoiceCalls
from apps.voice_calls.classes import NumberFormatter

@shared_task
def send_email_sims(id=None):
    
    orders_all = None
    if id == None:
        orders_all = Orders.objects.filter(order_status='EE')
    else:
        orders_all = Orders.objects.filter(pk=id)
        
    url_site = settings.URL_CDN
    url_img = f'{url_site}/email/'

    
    for order in orders_all:
        id = order.id
        name = order.client
        client_email = order.email
        order_id = order.item_id
        order_st = order.order_status
        try: qrcode = order.id_sim.link
        except: qrcode = None
        activation_date = order.activation_date
        product = f'{order.get_product_display()} {order.get_data_day_display()}'
        days = order.days     
        product_plan = order.get_product_display()
        try: type_sim = order.id_sim.type_sim
        except: continue            
        countries = order.countries
        
        context = {
            'url_site': url_site,
            'url_img': url_img,
            'name': name,
            'order_id': order_id,
            'qrcode': qrcode,
            'activation_date': activation_date,
            'product': product,
            'days': days,
            'product_plan': product_plan,
            'type_sim': type_sim,
            'countries': countries,        
        }
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
        
        if order_st != 'CN':
            # Update Order
            order = Orders.objects.get(pk=id)
            order.order_status = 'AA'
            order.save()
            # Update Store
            apiStore = ApiStore.conectApiStore()
            status_def_sis = StatusSis.st_sis_site()            
            update_store = {
                'status': status_def_sis['AA']
            }
            apiStore.put(f'orders/{order.order_id}', update_store).json()        
        
        # Add note
        add_note = Notes( 
            id_item = order,
            id_user = None,
            note = 'E-mail enviado com sucesso!',
            type_note = 'S',
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
        
        if order_st != 'CN':
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
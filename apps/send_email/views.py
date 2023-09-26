from django.shortcuts import redirect
from django.http import HttpResponse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib import messages
from apps.orders.models import Orders
from apps.orders.views import ApiStore, StatusSis

def send_email(request):
    orders_all = Orders.objects.filter(order_status='EE')
    url_site = 'https://painel.acasadochip.com'
    url_img = f'{url_site}/static/email/'
    
    if not orders_all:
        messages.info(request,f'Não há pedidos para enviar eSIMs!')
        return redirect('send_esims')
      
    for order in orders_all:
        name = order.client
        client_email = order.email
        order_id = order.item_id
        qrcode = order.id_sim.link
        
        activation_date = order.activation_date
        product = f'{order.get_product_display()} {order.get_data_day_display()}'
        days = order.days     
                   
        context = {
            'url_site': url_site,
            'url_img': url_img,
            'name': name,
            'order_id': order_id,
            'qrcode': qrcode,
            'activation_date': activation_date,
            'product': product,
            'days': days,        
        }
        html_content = render_to_string('painel/emails/send_esim.html', context)
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            #subject
            f"Entrega do eSIM PEDIDO #{order}",
            #content
            text_content,
            #from email
            settings.DEFAULT_FROM_EMAIL,
            #to
            [client_email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        # Up Status
        order_put = Orders.objects.get(pk=order.id)
        order_put.order_status = 'AA'
        order_put.save()
        
        apiStore = ApiStore.conectApiStore()                    
        apiStore.put(f'orders/{order.order_id}', {'status': 'agd-ativacao'}).json()

        print(f'Email enviado para {name} - {client_email} - {order.order_id}')
    
        # return HttpResponse('Email enviado com sucesso!')
        messages.success(request,f'E-mails enviados com sucesso!')
        
    return redirect('send_esims')
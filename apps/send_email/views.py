from django.shortcuts import redirect
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from apps.orders.models import Orders, Notes

class SendEmail():
    
    @staticmethod
    def mailAction(**kwargs):
        
        if kwargs.get('request'): request = kwargs.get('request')
        else: request = None
        if kwargs.get('id'): id = kwargs.get('id')
        else: id = None
        if kwargs.get('id_user'): id_user = kwargs.get('id_user')    
        else: id_user = None        
            
        if id == None:
            orders_all = Orders.objects.filter(order_status='EE')
        else:
            orders_all = Orders.objects.filter(pk=id)
            
        url_site = 'https://painel.acasadochip.com'
        url_img = f'{url_site}/static/email/'
        
        if not orders_all:           
            if id == None:
                messages.info(request, f'Não há pedidos para enviar eSIMs!')
                return redirect('send_esims')
            else:
                messages.info(request, f'Não há pedidos para enviar eSIMs!')
                return redirect('orders_list')            
        
        for order in orders_all:
            id = order.id
            name = order.client
            client_email = order.email
            order_id = order.item_id
            qrcode = order.id_sim.link
            activation_date = order.activation_date
            product = f'{order.get_product_display()} {order.get_data_day_display()}'
            days = order.days     
            product_plan = order.get_product_display()
            type_sim = order.id_sim.type_sim
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
            
            if id_user:               
                # Add note
                add_sim = Notes( 
                    id_item = Orders.objects.get(pk=id),
                    id_user = id_user,
                    note = 'E-mail enviado com sucesso!',
                    type_note = 'S',
                )
                add_sim.save()
                
        if request:
            messages.success(request,f'E-mail enviado com sucesso!!')
    
    def send_email(request,id):
        SendEmail.mailAction(id=id)      
        messages.success(request,f'E-mail enviado com sucesso!!')
        add_sim = Notes( 
            id_item = Orders.objects.get(pk=id),
            id_user = User.objects.get(pk=request.user.id),
            note = 'E-mail enviado com sucesso!',
            type_note = 'S',
        )
        add_sim.save()
        return redirect('orders_list')

    def send_email_all(id):
        SendEmail.mailAction(id=id)
        
    def send_email_esims(request):
        id_user = User.objects.get(pk=request.user.id)
        SendEmail.mailAction(request=request,id_user=id_user)
        return redirect('send_esims')
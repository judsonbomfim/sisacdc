import http
import json
import random
import string
from urllib.parse import urlparse
import pytz
import qrcode
import boto3
import time
import logging
from django.db.models import Q
from io import BytesIO
from datetime import datetime, timedelta
from django.conf import settings
from django.core.files.storage import default_storage
from celery import shared_task

logger = logging.getLogger(__name__)
from apps.voice_calls.classes import NoteVoiceCall, UpdateVoice
from apps.voice_calls.models import VoiceCalls, VoiceNumbers
from apps.send_email.tasks import send_email_voice


@shared_task
def voices_up_status(voice_id, voice_st):
    # Accept single id or list of ids
    ids = voice_id if isinstance(voice_id, (list, tuple)) else [voice_id]
    for v_id in ids:
        UpdateVoice.upStatus(v_id, voice_st)

@shared_task
def number_up_status(number_id, number_st):
       
    for num_id in number_id:
       
        # Save status System
        number = VoiceNumbers.objects.get(pk=num_id)
        number.number_status = number_st
        number.save()
        
        if number_st == 'AT':
            #send email
            send_email_voice.delay(num_id)

  
@shared_task
def update_password(number_id):
    
    for num_id in number_id:
        
        number = VoiceNumbers.objects.get(pk=num_id)
        del_file = number.number_qrcode
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        
        pref = 'Casa'
        pw = ''.join(random.choice('0123456789') for i in range(6))
        arc_name = ''.join(random.choice(string.ascii_letters) for i in range(6))
        number_pw = pref + pw
        
        data = f'csc:{number.login}:{number_pw}@PABX'
        filename = f'qrcode/qrcode-{number.extension}-{number.number}--{arc_name}.png'
        
        # QRCODE
        if number.number_qrcode != None:
            # Delete
            s3 = boto3.client('s3')
            s3.delete_object(Bucket=bucket, Key=del_file)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)    
        img = qr.make_image(fill='black', back_color='white')

        # Save in buffer
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Save System
        number.password = number_pw
        number.number_qrcode = filename
        number.save()
        
        # Save S3
        s3 = boto3.client('s3')
        s3.upload_fileobj(buffer, bucket, filename)
   

@shared_task
def number_in_voice():  # <- remover 'request'
    
    send_date = datetime.now().date() + timedelta(days=3)

    # Select Voice Calls
    voice_s = VoiceCalls.objects.filter(
        Q(call_status='PR', id_item__activation_date__lte=send_date) |
        Q(call_status='SL')
    )
        
    # Insert Number
    for vox in voice_s:
        id_vox = vox.id
        number_s = VoiceNumbers.objects.all().order_by('id').filter(number_status='DS').first()
        if not number_s:
            voice_put = VoiceCalls.objects.get(pk=id_vox)
            voice_put.call_status = 'EP'
            voice_put.save()
            continue
            
        # Change Status Voice
        voice_put = VoiceCalls.objects.get(pk=id_vox)
        voice_put.call_status = 'AA'
        voice_put.id_number = number_s
        voice_put.save()
        
        # Change Status Number
        number_s.number_status = 'AT'
        number_s.save()
        update_password.delay(number_id=[number_s.id])
        
        # Adicionar nota SEM request.user
        # Use um usuário padrão ou None
        from django.contrib.auth.models import User
        admin_user = User.objects.filter(is_superuser=True).first()  # pega um admin
        
        NoteVoiceCall.addNote(
            id_item=voice_put, 
            note=f"Ramal alterado - {number_s.extension}", 
            id_user=admin_user,  # <- use admin ou None
            type_note='P'
        )
        time.sleep(2)
        #send email
        # send_email_voice.delay(id_vox)
        
@shared_task
def voiceActivate(id=None):
             
    tz = pytz.timezone(settings.TIME_ZONE)
    today = datetime.now(tz).date()
    tomorrow = today + timedelta(days=2)
    
    logger.info('>>>>>>>>>> ATIVAÇÂO VOICE INICIADA')
    
    # Selecionar pedidos
    if id is None:
        voice_all = VoiceCalls.objects.filter(call_status='AA', activation_date__lte=tomorrow)
    else:
        voice_all = VoiceCalls.objects.filter(pk=id)        
    
    logger.error(f'>>>>>>>>>> Encontrados {voice_all.count()} pedidos de voz para processar')
    if voice_all.count() == 0:
        logger.info('>>>>>>>>>> Nenhum pedido de voz pendente. Aguardando próxima execução.')
        logger.info('>>>>>>>>>> ATIVAÇÂO VOICE FINALIZADA')
        return
    
    for order in voice_all:
        
        logger.error(f'Processando pedido ID: {order.id}')

        # Verifica se há número associado
        if order.id_number is None:
            logger.error(f'Pedido {order.id} sem número associado, pulando ativação')
            UpdateVoice.upStatus(order.id, 'EA')
            NoteVoiceCall.addNote(order, 'Erro: sem número associado para ativação')
            continue
        
        # order = VoiceCalls.objects.get(pk=order.id)
        order_id = order.id
        pedido = order.id_item.item_id
        username = order.id_number.login
        password = order.id_number.password
                
        # Dados para a solicitação
        url = f"{settings.APIVC_URL}ativar"
        parsed_url = urlparse(url)
        payload = json.dumps({
            "pedido": pedido,
            "cloud_username": username,
            "cloud_password": password
        })        
        headers = {
            'Content-Type': 'application/json',
            'x-painel-acdc-token': settings.APIVC_KEY
        }
        # Estabelece a conexão HTTPS
        conn = http.client.HTTPSConnection(parsed_url.netloc, timeout=10)
        # Envia a solicitação POST
        conn.request("POST", parsed_url.path, payload, headers)
        # Obtém a resposta
        res = conn.getresponse()
        data = res.read()
        # Decodifica a resposta
        try:
            response_data = json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, ValueError) as e:
            # API retornou resposta vazia ou inválida
            UpdateVoice.upStatus(order_id,'EA')
            NoteVoiceCall.addNote(order,f'Erro ao decodificar resposta da API. Status HTTP: {res.status}. Erro: {str(e)}')
            conn.close()
            continue
        
        # Verifica o código de resposta
        if response_data['status'] == "ok":
            # Alterar status
            UpdateVoice.upStatus(order_id,'AT')
            # Adicionar nota
            NoteVoiceCall.addNote(order,f'ATIVADO: "{response_data["message"]}"')
        elif response_data['status'] == "error":
            # Alterar status
            UpdateVoice.upStatus(order_id,'EA')
            # Adicionar nota
            NoteVoiceCall.addNote(order,f'{response_data["error_code"]}: "{response_data["message"]}"')    
        else:
            # Alterar status
            UpdateVoice.upStatus(order_id,'EA')
            # Adicionar nota
            NoteVoiceCall.addNote(order,f'ERRO: "{response_data["message"]}"')    

        # Fecha a conexão
        conn.close()
        
                
    logger.info('>>>>>>>>>> ATIVAÇÂO VOICE FINALIZADA')
    
@shared_task
def voiceDesactivate(id=None):
             
    timezone = pytz.timezone(settings.TIME_ZONE)
    now = datetime.now(timezone)
    yesterday = now.date() - timedelta(days=1)
    
    logger.info('>>>>>>>>>> DESATIVAÇÃO VOICE INICIADA')
    
    # Selecionar pedidos
    if id is None:
        voice_all = VoiceCalls.objects.filter(call_status='AT')
    else:
        voice_all = VoiceCalls.objects.filter(pk=id)
    
    logger.error(f'>>>>>>>>>> Encontrados {voice_all.count()} pedidos de voz para desativar')
    if not voice_all.exists():
        logger.info('>>>>>>>>>> Não há pedidos de voz para serem desativados.')
        logger.info('>>>>>>>>>> DESATIVAÇÃO VOICE FINALIZADA')
        return
    
    for order in voice_all:
        
        logger.error(f'Processando pedido ID: {order.id}')
          
        # Garante que activation_date e days não são nulos
        if order.activation_date is None or order.days is None:
            continue
        
        # Verifica se há número associado
        if order.id_number is None:
            UpdateVoice.upStatus(order.id, 'DS')
            NoteVoiceCall.addNote(order, 'Erro: sem número associado para ativação')
            logger.error(f'Pedido {order.id} sem número associado, pulando desativação')
            continue
        
        # Calcula a data de desativação
        # A lógica é: data de ativação + (duração do plano - 1 dia)
        deactivation_date = order.activation_date + timedelta(days=order.days - 1)

        # Se um ID específico não foi passado, só desativa se a data for ontem ou anterior
        if id is None and deactivation_date > yesterday:
            continue

        order_id = order.id
        pedido = order.id_item.item_id
        username = order.id_number.login
                
        # Dados para a solicitação
        url = f"{settings.APIVC_URL}desativar"
        parsed_url = urlparse(url)
        payload = json.dumps({
            "pedido": pedido,
            "cloud_username": username,
        })        
        headers = {
            'Content-Type': 'application/json',
            'x-painel-acdc-token': settings.APIVC_KEY
        }
        # Estabelece a conexão HTTPS
        conn = http.client.HTTPSConnection(parsed_url.netloc, timeout=10)
        # Envia a solicitação POST
        conn.request("POST", parsed_url.path, payload, headers)
        # Obtém a resposta
        res = conn.getresponse()
        data = res.read()
        # Decodifica a resposta
        try:
            response_data = json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, ValueError) as e:
            # API retornou resposta vazia ou inválida
            UpdateVoice.upStatus(order_id,'ED')
            NoteVoiceCall.addNote(order,f'Erro ao decodificar resposta de desativação. Status HTTP: {res.status}. Erro: {str(e)}')
            conn.close()
            continue
        
        # Verifica o código de resposta
        if response_data['status'] == "ok":
            # Alterar status
            UpdateVoice.upStatus(order_id,'DS')
            # Adicionar nota
            NoteVoiceCall.addNote(order,f'DESATIVADO: "{response_data["message"]}"')
        elif response_data['status'] == "error":
            # Alterar status
            UpdateVoice.upStatus(order_id,'ED')
            # Adicionar nota
            NoteVoiceCall.addNote(order,f'{response_data["error_code"]}: "{response_data["message"]}"')    
        else:
            # Alterar status
            UpdateVoice.upStatus(order_id,'ED')
            # Adicionar nota
            NoteVoiceCall.addNote(order,f'ERRO: "{response_data["message"]}"')    

        # Fecha a conexão
        conn.close()
                
    logger.info('>>>>>>>>>> DESATIVAÇÃO VOICE FINALIZADA')

# Aliases to match Celery Beat names configured in core.settings
@shared_task
def simActivateVC(id=None):
    return voiceActivate(id=id)

@shared_task
def simDeactivateVC(id=None):
    return voiceDesactivate(id=id)
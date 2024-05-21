import random
import string
import qrcode
import boto3
import time
from io import BytesIO
from datetime import datetime, timedelta
from django.conf import settings
from django.core.files.storage import default_storage
from celery import shared_task
from apps.voice_calls.models import VoiceCalls, VoiceNumbers
from apps.send_email.tasks import send_email_voice


@shared_task
def voices_up_status(voice_id, voice_st):
    for v_id in voice_id:
                
        voice_st = voice_st

        # Save status System
        voice = VoiceCalls.objects.get(pk=v_id)
        voice.call_status = voice_st
        voice.save()        
        
        if (voice_st == 'CC' or voice_st == 'DS') and voice.id_number != None:

            num = VoiceNumbers.objects.get(pk=voice.id_number.id)
            num.number_status = 'DS'
            num.save()
            
            voice.id_number = None
            voice.save()


@shared_task
def number_up_status(number_id, number_st):
       
    for num_id in number_id:
       
        number_id = number_id
        number_st = number_st

        # Save status System
        number = VoiceNumbers.objects.get(pk=num_id)
        number.number_status = number_st
        number.save()  

  
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
def number_in_voice():
    
    send_date = datetime.now().date() + timedelta(days=2)

    # Select Voice Calls
    voice_s = VoiceCalls.objects.filter(call_status='PR').filter(id_item__activation_date__lte=send_date)
    
    # Insert Number
    for vox in voice_s:
        id_vox = vox.id
        number_s = VoiceNumbers.objects.all().order_by('id').filter(number_status='DS').first()
        # Change Status Voice
        voice_put = VoiceCalls.objects.get(pk=id_vox)
        voice_put.call_status = 'AA'
        voice_put.id_number = number_s
        voice_put.save()
        # Change Status Number
        number_s.number_status = 'AT'
        number_s.save()
        update_password.delay(number_id=[number_s.id])
        time.sleep(2)
        #send email
        # send_email_voice.delay(id_vox)
from django.contrib.auth.models import User
from celery import shared_task
from apps.voice_calls.models import VoiceCalls, VoiceNumbers


@shared_task
def voices_up_status(voice_id, voice_st):
    for v_id in voice_id:
        
        print('----------------------------------v_id')
        print(v_id)
        
        voice_st = voice_st

        # Save status System
        voice = VoiceCalls.objects.get(pk=v_id)
        voice.call_status = voice_st
        voice.save()


@shared_task
def number_up_status(number_id, number_st):

    for num_id in number_id:

        print('----------------------------------num_id')
        print(num_id)
        
        number_id = number_id
        number_st = number_st

        # Save status System
        number = VoiceNumbers.objects.get(pk=num_id)
        number.number_status = number_st
        number.save()
        


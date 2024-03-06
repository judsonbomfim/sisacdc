from django.contrib.auth.models import User
from celery import shared_task
from apps.voice_calls.models import VoiceCalls, VoiceNumbers

@shared_task
def number_up_status(number_id, number_st, id_user):

    for num_id in number_id:
        
        number_id = number_id
        number_st = number_st

        # Save status System
        number = VoiceNumbers.objects.get(pk=num_id)
        number.number_status = number_st
        number.save()
        


from .models import NotesVoice, VoiceCalls, VoiceNumbers
import logging
logger = logging.getLogger(__name__)

class NumberFormatter:
    @staticmethod
    def format(num):
        num = str(num)
        p1 = num[0:2]
        p2 = num[2:6]
        p3 = num[6:11]
        num_f = f'({p1}) {p2}-{p3}'
        return num_f

class NoteVoiceCall:
    @staticmethod
    def addNote(id_item, note, id_user=None, type_note='S'):
        try:           
            # Criar e salvar a nota
            nota = NotesVoice.objects.create(
                id_item=id_item,
                note=note,
                id_user=id_user,
                type_note=type_note
            )            
            return nota
            
        except Exception as e:
            logger.error(f"  ERRO ao criar nota: {e}")
            return None

class UpdateVoice():
    @staticmethod
    def upStatus(order_id,order_st):
        voice = VoiceCalls.objects.get(pk=order_id)
        # Disponibilizar número quando desativado
        if order_st == 'DS' and voice.id_number is not None:
            num = VoiceNumbers.objects.get(pk=voice.id_number.id)
            num.number_status = 'DS'
            num.save()
            voice.id_number = None
        
        voice.call_status = order_st
        voice.save()
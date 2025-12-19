from .models import NotesVoice, VoiceCalls, VoiceNumbers


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
            
            print(f"  Nota criada com ID: {nota.id}")
            return nota
            
        except Exception as e:
            print(f"  ERRO ao criar nota: {e}")
            return None

class UpdateVoice():
    @staticmethod
    def upStatus(order_id,order_st):
        from apps.voice_calls.tasks import voiceActivate, voiceDesactivate
        
        voice = VoiceCalls.objects.get(pk=order_id)
        voice_id = voice.id

        # Alterar status na Operadora
        if order_st == 'AT' and voice.id_number != None:
            voiceActivate(voice_id)
        elif order_st == 'DS' and voice.id_number != None:
            voiceDesactivate(voice_id)
            # Disponibilizar número        
            num = VoiceNumbers.objects.get(pk=voice.id_number.id)
            num.number_status = 'DS'
            num.save()
            voice.id_number = None
        
        voice.call_status = order_st
        voice.save()
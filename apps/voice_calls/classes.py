from apps.voice_calls.models import NotesVoice, VoiceCalls


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
    def addNote(id_item,note,id_user=None,type_note='S'):
        add_note = NotesVoice( 
            id_item = id_item,
            id_user = id_user,
            note = note,
            type_note = type_note,
        )
        add_note.save()
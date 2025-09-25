from .models import NotesVoice


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
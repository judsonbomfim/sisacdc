from django.shortcuts import render
from django.contrib import messages
from apps.voice_calls.models import VoiceNumbers


def voice_index(request):
    return render(request, 'painel/voice/index.html')

def voice_import(request):
    if request.method == "GET":
        return render(request, 'painel/voice/import.html')
 
    if request.method == 'POST':
        try:
            voice = request.FILES.get('voice')
        except: voice = ''
        ext_name = str(voice)
        ext = ext_name[-3:]
        
        # Validations File
        if ext != 'csv':
            messages.error(request,'O arquivo está incorreto. Verifique por favor!')
            return render(request, 'painel/voice/import.html')     
        if voice == '':
            messages.error(request,'Campo obrigatório!')
            return render(request, 'painel/voice/import.html')
        
        # Validation field empty
        if voice != '':
            arquivo = voice.read().decode("utf-8")
            line_h = 0            
            for lines in arquivo.split('\n'):
                                
                line = []
                col = lines.split(',')
                line.append(col)
                
                f_login = line[0][0]
                f_extension = line[0][1]
                f_number = line[0][2]
                
                # Validate first line
                if line_h == 0:
                    if f_login == 'conta_sip':
                        line_h += 1
                        continue
                    else:
                        messages.error(request,'Houve um erro ao gravar a lista. Verifique se o arquivo está no formato correto')
                        return render(request, 'painel/voice/import.html')
                
                # Validate fields
                if f_login == '' or f_extension == '' or f_number == '':
                    messages.error(request,'Erro ao gravar linha')
                    continue
                
                # Validate voice
                voice_all = VoiceNumbers.objects.filter(login=f_login).exists()
                if voice_all:
                    messages.info(request,f'O SIM {line} >>> já está cadastrado no sistema <<<')
                    continue
                    
                # Save SIMs
                add_voice = VoiceNumbers(
                    login = f_login,
                    extension = f_extension,
                    number = f_number
                )
                add_voice.save()
                
            messages.success(request,f'Lista {line} gravada com sucesso')
            return render(request, 'painel/voice/import.html')
        else:
            messages.error(request,'Houve um ero ao gravar a lista. Verifique se o arquivo está no formato correto')
            return render(request, 'painel/voice/import.html')

def voice_edit(request):
    return render(request, 'painel/voice/edit.html')
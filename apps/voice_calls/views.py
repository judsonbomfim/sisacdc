from django.shortcuts import render

def voice_list(request):
    return render(request, 'painel/voice/index.html')

def voice_import(request):
    return render(request, 'painel/voice/index.html')

def voice_edit(request):
    return render(request, 'painel/voice/index.html')
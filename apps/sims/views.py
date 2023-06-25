from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.messages import constants
from requests import request
from apps.sims.models import Sims
from apps.sims.forms import addSims

def sims_list(request):
    sims = Sims.objects.all()
    return render(request, 'painel/sims/index.html', {'sims': sims})

def sims_add(request):
    if request.method == "GET":
        
        return render(request, 'painel/sims/add.html')
        
    if request.method == 'POST':
        
        type_sim = request.POST.get('type_sim')
        operator = request.POST.get('operator')
        sim = request.FILES.get('sim')
        ext_nome = str(sim)
        ext = ext_nome[-3:]
        print(ext)        
        
        # Validations
        if ext != 'csv':
            messages.error(request,'O arquivo não é um CSV')
            return render(request, 'painel/sims/add.html')     
        if type_sim == '' or operator == '' or sim == '':
            messages.error(request,'Preencha todos os campos')
            return render(request, 'painel/sims/add.html')
        
        try:
            arquivo = sim.read().decode("utf-8")
            linha_h = 0
            for linha in arquivo.split():
                # Validate first line
                if linha == 0:
                    if linha == 'upload_sims':
                        linha_h += 1
                        continue
                    else:
                        messages.error(request,'Houve um erro ao gravar a lista. Verifique se o arquivo está no formato correto')
                        return render(request, 'painel/sims/add.html')
                               
                # Save SIMs
                add_sim = Sims(
                    sim = linha,
                    type_sim = type_sim,
                    operator = operator
                )
                add_sim.save()
                
            messages.success(request,'Lista gravada com sucesso')
            return render(request, 'painel/sims/add.html')
        except:
            messages.error(request,'Houve um ero ao gravar a lista. Verifique se o arquivo está no formato correto')
            return render(request, 'painel/sims/add.html')
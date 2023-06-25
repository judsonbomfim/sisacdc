from django.shortcuts import render
from requests import request
from apps.sims.models import Sims
from apps.sims.forms import addSims

# def carregaArquivo(arqcsv):
#     arquivo = open(arqcsv,"r",encoding="utf-8")
#     dados = []
#     for linha in arquivo:
#         linha1 = linha[:-1].split(",")
#         dados.append(linha1)
#     arquivo.close()
#     return dados

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
        
        arquivo = sim.read().decode("utf-8")
        sim_n = []
        for linha in arquivo.split():
            linha1 = linha
            sim_n.append(linha1)
            
            # Save SIMs
            add_sim = Sims(
                 sim = linha1,
                type_sim = type_sim,
                operator = operator
            )
            add_sim.save()
        
        
        return render(request, 'painel/sims/add.html')
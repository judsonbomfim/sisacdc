from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from apps.sims.models import Sims

def sims_list(request):
    sims = Sims.objects.all()
    return render(request, 'painel/sims/index.html', {'sims': sims})

def sims_add_sim(request):
    if request.method == "GET":
        
        return render(request, 'painel/sims/add-sim.html')
        
    if request.method == 'POST':
        
        type_sim = request.POST.get('type_sim')
        operator = request.POST.get('operator')
        sim = request.FILES.get('sim')
        ext_nome = str(sim)
        ext = ext_nome[-3:]
        
        # Validations
        if ext != 'csv':
            messages.error(request,'O arquivo não é um CSV')
            return render(request, 'painel/sims/add-sim.html')     
        if type_sim == '' or operator == '' or sim == '':
            messages.error(request,'Preencha todos os campos')
            return render(request, 'painel/sims/add-sim.html')
        
        try:
            arquivo = sim.read().decode("utf-8")
            linha_h = 0
            for linha in arquivo.split():
                # Validate first line
                if linha_h == 0:
                    if linha == 'upload_sims':
                        linha_h += 1
                        continue
                    else:
                        messages.error(request,'Houve um erro ao gravar a lista. Verifique se o arquivo está no formato correto')
                        return render(request, 'painel/sims/add-sim.html')
                               
                # Save SIMs
                print(linha_h)
                add_sim = Sims(
                    sim = linha,
                    type_sim = type_sim,
                    operator = operator
                )
                add_sim.save()
                
            messages.success(request,'Lista gravada com sucesso')
            return render(request, 'painel/sims/add-sim.html')
        except:
            messages.error(request,'Houve um ero ao gravar a lista. Verifique se o arquivo está no formato correto')
            return render(request, 'painel/sims/add-sim.html')

def sims_add_esim(request):
    if request.method == "GET":
        
        return render(request, 'painel/sims/add-esim.html')
        
    if request.method == 'POST':
                
        type_sim = request.POST.get('type_sim')
        operator = request.POST.get('operator')
        esims = request.FILES.getlist('esim')
 
        if type_sim == '' or operator == '' or esims == '':
            messages.error(request,'Preencha todos os campos')
            return render(request, 'painel/sims/add-esim.html')
                           
        try:
            for sim_img in esims:
                # Save SIMs
                add_sim = Sims(
                    sim = sim_img.name[0:-5],
                    link = sim_img.name,
                    type_sim = type_sim,
                    operator = operator
                )
                add_sim.save()
                # Save image
                fs = FileSystemStorage()
                fs.save(sim_img.name, sim_img)

            messages.success(request,'Lista gravada com sucesso')
            return render(request, 'painel/sims/add-esim.html')
        except:
            messages.error(request,'Houve um erro ao gravar os eSIMs')
            return render(request, 'painel/sims/add-esim.html')
from django.contrib.auth.decorators import login_required
from rolepermissions.decorators import has_permission_decorator
from django.shortcuts import render
from django.http import HttpResponse
from django.urls import reverse
import csv
import os
import imghdr
from datetime import date
from django.core.paginator import Paginator
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from apps.sims.models import Sims
from apps.orders.models import Orders
from apps.orders.views import ApiStore, StatusStore
import boto3
from django.conf import settings
from django.core.files.storage import default_storage
from .tasks import sims_in_orders


# Script Upload S3
def get_s3_client():
    return boto3.client(
        's3', 
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID, 
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )

def upload_file_to_s3(file):
    s3 = get_s3_client()
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    file_path = f"{settings.MEDIA_LOCATION}/{file.name}"
    s3.upload_fileobj(file, bucket_name, file_path)
    return default_storage.url(file_path)

@login_required(login_url='/login/')
@has_permission_decorator('view_sims')
def sims_list(request):
    global sims_l
    sims_l = ''
    
    sims_all = Sims.objects.all().order_by('-id')
    sims_l = sims_all
    url_cdn = settings.URL_CDN
    
    if request.method == 'GET':
        
        sim_f = request.GET.get('sim')
        sim_type_f = request.GET.get('sim_type')    
        sim_status_f = request.GET.get('sim_status')
        sim_oper_f = request.GET.get('sim_oper')
    
    if request.method == 'POST':
        
        sim_f = request.POST.get('sim_f')
        sim_type_f = request.POST.get('sim_type_f')       
        sim_status_f = request.POST.get('sim_status_f')
        sim_oper_f = request.POST.get('sim_oper_f')
            
        if 'up_status' in request.POST:
                sim_id = request.POST.getlist('sim_id')
                sim_st = request.POST.get('sim_st')
                if sim_id and sim_st:
                    for o_id in sim_id:
                        sim = Sims.objects.get(pk=o_id)
                        sim.sim_status = sim_st
                        sim.save()
                        
                    messages.success(request,f'SIM(s) atualizado(s) com sucesso!')
                else:
                    messages.info(request,f'Você precisa marcar alguma opção')
    
    # FIlters
    
    url_filter = ''
    
    if sim_f:
        sims_l = sims_l.filter(sim__icontains=sim_f)
        url_filter += f"&sim={sim_f}"

    if sim_type_f: 
        sims_l = sims_l.filter(type_sim__icontains=sim_type_f)        
        url_filter += f"&sim_type={sim_type_f}"
    
    if sim_status_f: 
        sims_l = sims_l.filter(sim_status__icontains=sim_status_f)
        url_filter += f"&sim_status={sim_status_f}"
    
    if sim_oper_f: 
        sims_l = sims_l.filter(operator__icontains=sim_oper_f)
        url_filter += f"&sim_oper={sim_oper_f}"
        
    
    sims_types = Sims.type_sim.field.choices
    sims_status = Sims.sim_status.field.choices
    sims_oper = Sims.operator.field.choices
    
    paginator = Paginator(sims_l, 50)
    page = request.GET.get('page')
    sims = paginator.get_page(page)
    
    # Verificar estoque de operadoras
    sim_tm = sims_all.filter(sim_status='DS',operator='TM', type_sim='sim').count()
    esim_tm = sims_all.filter(sim_status='DS',operator='TM', type_sim='esim').count()
    sim_cm = sims_all.filter(sim_status='DS',operator='CM', type_sim='sim').count()
    esim_cm = sims_all.filter(sim_status='DS',operator='CM', type_sim='esim').count()
    sim_tc = sims_all.filter(sim_status='DS',operator='TC', type_sim='sim').count()
    esim_tc = sims_all.filter(sim_status='DS',operator='TC', type_sim='esim').count()
    
    url = reverse('sims_index')
    
    context= {
        'url': url,
        'url_cdn': url_cdn,
        'sims': sims,
        'sims_types': sims_types,
        'sims_status': sims_status,
        'sims_oper': sims_oper,
        'sim_tm': sim_tm,
        'esim_tm': esim_tm,
        'sim_cm': sim_cm,
        'esim_cm': esim_cm,
        'sim_tc': sim_tc,
        'esim_tc': esim_tc,
        'url_filter': url_filter,
    }
       
    return render(request, 'painel/sims/index.html', context)

@login_required(login_url='/login/')
@has_permission_decorator('add_sims')
def sims_add_sim(request):
    if request.method == "GET":
        
        url_cdn = settings.URL_CDN
        
        context = {
            'url_cdn': url_cdn,
        }
        
        return render(request, 'painel/sims/add-sim.html', context)
        
    if request.method == 'POST':
        
        type_sim = request.POST.get('type_sim')
        operator = request.POST.get('operator')
        sim = request.FILES.get('sim')
        ext_nome = str(sim)
        ext = ext_nome[-3:]
        
        # Validations
        if ext != 'csv':
            messages.error(request,'O arquivo está incorreto. Verifique por favor!')
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
                
                sims_all = Sims.objects.all().filter(sim=linha).filter(type_sim='sim')
                if sims_all:
                    messages.info(request,f'O SIM {linha} já está cadastrado no sistema')
                    continue
                  
                # Save SIMs
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

@login_required(login_url='/login/')
@has_permission_decorator('edit_sims')
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
                           
        
        for sim_img in esims:
            sim_i = sim_img.name.split('.')
            
            print(sim_img.name)
            print(sim_img)
            
            fileurl = ''
            if imghdr.what(sim_img):
                fileurl = upload_file_to_s3(sim_img)
                fileurl = fileurl.replace(settings.URL_CDN,'')
            else:
                messages.error(request,'O arquivo não é uma imagem. Verifique por favor!')
                return render(request, 'painel/sims/add-esim.html')           

            
            sims_all = Sims.objects.all().filter(sim=sim_i[0]).filter(type_sim='esim')
            if sims_all:
                messages.info(request,f'O SIM {sim_i[0]} já está cadastrado no sistema')
                continue
            # Save SIMs
            add_sim = Sims(
                sim = sim_i[0],
                link = fileurl,
                type_sim = type_sim,
                operator = operator
            )
            add_sim.save()

        messages.success(request,'Lista gravada com sucesso')
        return render(request, 'painel/sims/add-esim.html')

@login_required(login_url='/login/')
@has_permission_decorator('add_ord_sims')
def sims_ord(request):
    if request.method == "GET":
        return render(request, 'painel/sims/sim-order.html')
    
    if request.method == 'POST':
        
        sims_in_orders.delay()
        messages.success(request, f'Processando SIMs... Aguarde alguns minutos e atualize a página de pedidos')        
        
    return render(request, 'painel/sims/sim-order.html')

@login_required(login_url='/login/')
@has_permission_decorator('export_activations')
def exportSIMs(request):
    
    sims_all = Sims.objects.all().order_by('id')
    data = [
        ['ID', 'SIM', 'Tipo', 'Operadora', 'Status']
    ]
    for sim in sims_all:
        data.append([sim.id,sim.sim,sim.type_sim,sim.operator,sim.sim_status])
    
    data_atual = date.today()
    # Crie um objeto CSVWriter para escrever os dados no formato CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="Estoque SIMs-{data_atual}.csv"'
    writer = csv.writer(response)

    # Escreva os dados no objeto CSVWriter
    for row in data:
        writer.writerow(row)

    return response

@login_required(login_url='/login/')
def delSIMs(request):
    orders = Orders.objects.all()
    
    sims_cc = Sims.objects.filter(sim_status='CC')
    sims_tc = Sims.objects.filter(sim_status='TC')
    
    for sim in sims_cc:
        if orders.filter(id_sim=sim.id):
            continue
        sim.delete()
    
    for sim in sims_tc:
        if orders.filter(id_sim=sim.id):
            continue
        sim.delete()
    
    return HttpResponse('SIMs deletados com sucesso')

@login_required(login_url='/login/')
def delSimTC(request):
    list_icc = {
        '8932042000002327335',
        '8932042000002327334',
        '8932042000002327333',
        '8932042000002327332',
        '8932042000002327331',
        '8932042000002327330',
        '8932042000002327329',
        '8932042000002327328',
        '8932042000002327327',
        '8932042000002327326',
    }
    
    sims = Sims.objects.filter(type_sim='esim', operator='TC')
    
    for sim in sims:
        sim_iccid = sim.sim
        if sim_iccid not in list_icc:
            sim.orders_set.all().update(id_sim=None)  # Set foreign key to NULL in related Order objects
            sim.delete()
            print(f'SIM {sim_iccid} deletado com sucesso!')
        else:
            print(f'SIM {sim_iccid} não deletado!')
    
    print('>>>>>>>>>>>>>>>>>>> FINALIZADO')
    return HttpResponse('SIMs deletados com sucesso')


@login_required(login_url='/login/')
def apiTestCM(request):
    
    import base64
    import hashlib
    import json
    import http.client
    from urllib.parse import urlparse
    import time

    def generate_password_digest(app_secret):
        nonce = str(int(time.time() * 1000))
        created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        digest = base64.b64encode(hashlib.sha256((nonce + created + app_secret).encode('utf-8')).digest()).decode('utf-8')
        return nonce, created, digest

    # URL do endpoint
    url = "https://gdschannel.cmlink.com:39043/aep/APP_createOrder_SBO/v1"
    parsed_url = urlparse(url)
    app_key = "b66505d9f87e4b68adead845764eb8d1"
    app_secret = "65e4507f61804077bb1058b73bf1eba0"

    # Gerar PasswordDigest
    nonce, created, password_digest = generate_password_digest(app_secret)

    # Cabeçalhos da requisição
    headers = {
        'Content-Type': 'application/json',
        "Accept": "application/json",
        "Authorization": 'WSSE realm="SDP", profile="UsernameToken", type="Appkey"',
        "X-WSSE": f'UsernameToken Username="{app_key}", PasswordDigest="{password_digest}", Nonce="{nonce}", Created="{created}"',
    }

    # Corpo da requisição
    payload = json.dumps({
        "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJyb2xlIjoxMDYsInVzZXJpZCI6ImI2NjUwNWQ5Zjg3ZTRiNjhhZGVhZDg0NTc2NGViOGQxIiwiaWF0IjoxNzI5NTk2NTY0fQ.Ss8oXd-FtQz9iynUbZyCTW3Ue-7GxmJLugCsA0Sj_MYiUm69HmPGOLOH1YkJswNv4bVlsi8x6Dqg5nBlZm8BHw",
        "iccid": "8932042000002035349",
        "dataBundleId": "D181029093919_215465",
    })

    # Fazer a requisição POST com tempo limite
    try:
        conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, timeout=10)
        conn.request("POST", parsed_url.path, payload, headers)
        res = conn.getresponse()

        # Verificar o status da resposta
        print(res.status, res.reason)
        data = res.read()
        print(data.decode('utf-8'))
    finally:
        conn.close()
    
    return HttpResponse("Resposta da API")

# @login_required(login_url='/login/')
# def verify_sim(request):
#     simsAT = Sims.objects.all().filter(sim_status='AT').filter(type_sim='sim')
#     simsDS = Sims.objects.all().filter(sim_status='DS').filter(type_sim='sim')
#     simsTC = Sims.objects.all().filter(sim_status='TC')
#     orders = Orders.objects.all()

#     print('>>>>>> SIMs Ativados sem pedidos')
#     print('----------------------------------')
#     for simAT in simsAT:    
#         if orders.filter(id_sim__sim=simAT.sim):
#             continue
#         else:
#             print(simAT.sim,simAT.type_sim)
            
#     print('>>>>>> SIMs Disponíveis com pedidos')
#     print('----------------------------------')
#     for simDS in simsDS:
#         if orders.filter(id_sim__sim=simDS.sim):
#             print(simDS.sim,simDS.type_sim)
#         else:
#             continue
    
#     print('>>>>>> SIMs Troca com pedidos')
#     print('----------------------------------')
#     for simTC in simsTC:
#         if orders.filter(id_sim__sim=simTC.sim):
#             print(simTC.sim,simDS.type_sim)
#         else:
#             continue
            
#     return HttpResponse('Links corrigidos com sucesso')
import csv
import io
import boto3
from django.contrib.auth.decorators import login_required
from rolepermissions.decorators import has_permission_decorator
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.urls import reverse
from django.core.paginator import Paginator
from django.contrib import messages
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from datetime import date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..serializers import ConsumoSerializer
from apps.sims.classes import ApiTC, ApiCM, qrcodeChange
from rest_framework.permissions import IsAuthenticated
from apps.sims.models import Sims
from ..tasks import simDeactivateTC, sims_in_orders
import logging
logger = logging.getLogger(__name__)

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
    if hasattr(file, 'seek'):
        file.seek(0)
    s3.upload_fileobj(file, bucket_name, file_path)
    return default_storage.url(file_path)


def get_operator_data(oper_val):
    if oper_val == 'OR20':
        return 'OR', '20gb'
    if oper_val == 'OR50':
        return 'OR', '50gb'
    if oper_val == 'ORWD':
        return 'OR', 'world'
    return oper_val, ''


def normalize_csv_row(row):
    normalized = {}
    for key, value in row.items():
        if key is None:
            continue
        normalized[key.strip().lower()] = value.strip() if isinstance(value, str) else value
    return normalized


def get_csv_value(row, *keys):
    for key in keys:
        value = row.get(key)
        if value:
            return value.strip()
    return ''


def build_qr_file(lpa, sim):
    qr_image = qrcodeChange.convert_qr_code(lpa)
    qr_image = qr_image.get_image() if hasattr(qr_image, 'get_image') else qr_image

    image_buffer = io.BytesIO()
    qr_image.save(image_buffer, format='JPEG')
    return ContentFile(image_buffer.getvalue(), name=f'{sim}.jpg')

@login_required(login_url='/login/')
@has_permission_decorator('view_sims')
def sims_list(request):
    sims_all = Sims.objects.all().order_by('-id')
    sims_l = sims_all
    url_cdn = settings.URL_CDN
    
    # Obter parâmetros de filtro (tanto GET quanto POST)
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
    
    # Aplicar filtros
    url_filter = ''
    
    if sim_f:
        sims_l = sims_l.filter(sim__icontains=sim_f)
        url_filter += f"&sim={sim_f}"

    if sim_type_f: 
        sims_l = sims_l.filter(type_sim=sim_type_f)        
        url_filter += f"&sim_type={sim_type_f}"
    
    if sim_status_f: 
        sims_l = sims_l.filter(sim_status=sim_status_f)
        url_filter += f"&sim_status={sim_status_f}"
    
    if sim_oper_f: 
        sims_l = sims_l.filter(operator=sim_oper_f)
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
    sim_ti = sims_all.filter(sim_status='DS',operator='TI', type_sim='sim').count()
    esim_ti = sims_all.filter(sim_status='DS',operator='TI', type_sim='esim').count()
    sim_ms = sims_all.filter(sim_status='DS',operator='MS', type_sim='sim').count()
    esim_ms = sims_all.filter(sim_status='DS',operator='MS', type_sim='esim').count()
    esim_or_20gb = sims_all.filter(sim_status='DS',operator='OR', type_sim='esim', data='20gb').count()
    esim_or_50gb = sims_all.filter(sim_status='DS',operator='OR', type_sim='esim', data='50gb').count()
    esim_or_world = sims_all.filter(sim_status='DS',operator='OR', type_sim='esim', data='world').count()
    
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
        'sim_ti': sim_ti,
        'esim_ti': esim_ti,
        'sim_ms': sim_ms,
        'esim_ms': esim_ms,
        'esim_or_20gb': esim_or_20gb,
        'esim_or_50gb': esim_or_50gb,
        'esim_or_world': esim_or_world,
        'url_filter': url_filter,
        'sim_f': sim_f,
        'sim_type_f': sim_type_f,
        'sim_status_f': sim_status_f,
        'sim_oper_f': sim_oper_f,
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
        oper_val = request.POST.get('operator')
        operator, data = get_operator_data(oper_val)
        esim_file = request.FILES.get('esim')
 
        if type_sim == '' or operator == '' or not esim_file:
            messages.error(request,'Preencha todos os campos')
            return render(request, 'painel/sims/add-esim.html')

        if not esim_file.name.lower().endswith('.csv'):
            messages.error(request,'O arquivo está incorreto. Envie uma planilha CSV.')
            return render(request, 'painel/sims/add-esim.html')

        try:
            decoded_file = esim_file.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            messages.error(request,'Não foi possível ler o CSV. Salve a planilha em UTF-8 e tente novamente.')
            return render(request, 'painel/sims/add-esim.html')

        reader = csv.DictReader(io.StringIO(decoded_file))
        if not reader.fieldnames:
            messages.error(request,'A planilha CSV está vazia ou sem cabeçalho.')
            return render(request, 'painel/sims/add-esim.html')

        normalized_headers = [header.strip().lower() for header in reader.fieldnames if header]
        if 'lpa' not in normalized_headers or not any(header in normalized_headers for header in ['sim', 'iccid']):
            messages.error(request,'A planilha deve conter as colunas lpa e sim ou iccid.')
            return render(request, 'painel/sims/add-esim.html')

        created_total = 0
        skipped_total = 0

        for row_number, row in enumerate(reader, start=2):
            normalized_row = normalize_csv_row(row)
            sim_value = get_csv_value(normalized_row, 'sim', 'iccid')
            lpa_value = get_csv_value(normalized_row, 'lpa')

            if not sim_value or not lpa_value:
                skipped_total += 1
                messages.info(request, f'Linha {row_number} ignorada: sim/iccid ou lpa ausente.')
                continue

            sim_exists = Sims.objects.filter(sim=sim_value, type_sim='esim').exists()
            if sim_exists:
                skipped_total += 1
                messages.info(request, f'O SIM {sim_value} já está cadastrado no sistema')
                continue

            qr_file = build_qr_file(lpa_value, sim_value)
            fileurl = upload_file_to_s3(qr_file).replace(f'https://{settings.AWS_S3_CUSTOM_DOMAIN}', '')

            add_sim = Sims(
                sim=sim_value,
                lpa=lpa_value,
                link=fileurl,
                type_sim=type_sim,
                data=data,
                operator=operator
            )
            add_sim.save()
            created_total += 1

        if created_total == 0 and skipped_total > 0:
            messages.warning(request, 'Nenhum eSIM novo foi gravado. Verifique as linhas ignoradas.')
            return render(request, 'painel/sims/add-esim.html')

        messages.success(request, f'Lista gravada com sucesso. {created_total} eSIM(s) cadastrado(s).')
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
def alterarOperadora(request):
    sims = Sims.objects.all().filter(operator='TC', type_sim='sim', sim_status='DS')
    
    for sim in sims:
        sim.operator = 'TI'
        sim.save()
    
    return HttpResponse('Operadora alterada com sucesso!')


class ConsumoView(APIView):
    permission_classes = [IsAuthenticated]  # Requer autenticação JWT

    def get(self, request, iccid):
        try:
            # Chama o método mobileData da classe ApiTC
            mobile_data = ApiTC.mobileData(iccid)
            # Serializa os dados
            serializer = ConsumoSerializer(data={
                "iccid": iccid,
                "mobile_data": mobile_data
            })
            if serializer.is_valid():
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Tratamento genérico de erros
            return Response({"error": f"Erro ao consultar consumo: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

@login_required(login_url='/login/')
def testeMobileData(request, iccid):
    
    try:
        # Verificar se a classe foi importada corretamente
        logger.info(f"Classe ApiCM disponível: {ApiCM}")        
        # Chamar método mobileData da classe ApiCM
        mobile_data = ApiCM.mobileData(iccid)        
        # Retornar resposta JSON
        return JsonResponse({
            'success': True,
            'iccid': iccid,
            'mobile_data': mobile_data,
            'operator': 'CM'
        })
        
    except Exception as e:
        logger.error(f"Erro em testeMobileDataCM: {e}")
        
        return JsonResponse({
            'success': False,
            'error': str(e),
            'iccid': iccid
        }, status=500)


def desativarTM(request):
    simDeactivateTC.delay()
    return HttpResponse('Processando desativações... Aguarde alguns minutos e atualize a página de pedidos')

def lpaChange(request):
    sims = Sims.objects.filter(type_sim='esim', sim_status='DS', lpa='').order_by('id')
    contagem = 0
    for sim in sims:
        link_qrcode = F"https://{settings.AWS_S3_CUSTOM_DOMAIN}{sim.link}"
        try:
            new_lpa = qrcodeChange.read_qr_code(link_qrcode)
            if new_lpa:
                sim.lpa = new_lpa
                sim.save()
            contagem += 1
            logger.info(f"Processado SIM: {sim.sim} - TOTAL: {contagem}/{sims.count()}")
        except Exception as e:
            logger.error(f"Erro ao atualizar LPA para SIM {sim.sim}: {e}")
    return HttpResponse('Processando atualização de LPA... Aguarde alguns minutos e atualize a página de pedidos')

def deleteSIM(request):
    sims = Sims.objects.filter(sim_status='IN')
    s3 = get_s3_client()
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    for sim in sims:
        if sim.link and sim.link != '-':
            file_path = sim.link.lstrip('/')
            try:
                s3.delete_object(Bucket=bucket_name, Key=file_path)
            except Exception as e:
                logger.error(f"Erro ao excluir arquivo S3 do SIM {sim.sim}: {e}")
        sim.delete()
    return HttpResponse('Processando exclusão de SIMs... Aguarde alguns minutos e atualize a página de pedidos')
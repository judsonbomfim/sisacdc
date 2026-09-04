import operator
from django.contrib.auth.models import User
from rolepermissions.decorators import has_permission_decorator
import csv
from django.http import HttpResponse, JsonResponse
from datetime import date, datetime, timedelta
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.conf import settings
from django.db.models import Count, Q
from django.urls import reverse
from urllib.parse import urlencode
from apps.orders.models import Orders, Notes
from apps.sims.classes import ApiTC, ApiCM, ApiCMHK
from apps.sims.models import Sims
from apps.send_email.tasks import send_email_sims
from apps.sims.tasks import simDeactivateTC, simActivateTC
from apps.voice_calls.models import VoiceCalls
from .classes import ApiStore, NoteStore, StatusStore, DateFormats, UpdateStore, ExportClients
from .tasks import order_import, orders_up_status, update_st
import pandas as pd


#Date today
today = datetime.now()

ORDERS_LIST_PER_PAGE_CHOICES = (25, 50, 100, 200)
ORDERS_LIST_DEFAULT_PER_PAGE = 50

def _orders_list_params(request):
    """Lê filtros da listagem (GET/POST) e normaliza per_page."""
    src = request.POST if request.method == 'POST' else request.GET
    q = (src.get('q') or '').strip()
    oper_f = (src.get('oper') or src.get('oper_f') or '').strip()
    ord_st_f = (src.get('ord_st') or src.get('ord_st_f') or '').strip()
    # Compatibilidade com filtros antigos
    ord_name_f = (src.get('ord_name') or src.get('ord_name_f') or '').strip()
    ord_order_f = (src.get('ord_order') or src.get('ord_order_f') or '').strip()
    ord_sim_f = (src.get('ord_sim') or src.get('ord_sim_f') or '').strip()

    try:
        per_page = int(src.get('per_page') or ORDERS_LIST_DEFAULT_PER_PAGE)
    except (TypeError, ValueError):
        per_page = ORDERS_LIST_DEFAULT_PER_PAGE
    if per_page not in ORDERS_LIST_PER_PAGE_CHOICES:
        per_page = ORDERS_LIST_DEFAULT_PER_PAGE

    return {
        'q': q,
        'oper': oper_f,
        'ord_st': ord_st_f,
        'ord_name': ord_name_f,
        'ord_order': ord_order_f,
        'ord_sim': ord_sim_f,
        'per_page': per_page,
    }

def _apply_orders_list_filters(qs, params):
    q = params.get('q')
    if q:
        qs = qs.filter(
            Q(client__icontains=q)
            | Q(item_id__icontains=q)
            | Q(id_sim__sim__icontains=q)
            | Q(id_sim__lpa__icontains=q)
        )

    if params.get('ord_name'):
        qs = qs.filter(client__icontains=params['ord_name'])
    if params.get('ord_order'):
        qs = qs.filter(item_id__icontains=params['ord_order'])
    if params.get('ord_sim'):
        qs = qs.filter(id_sim__sim__icontains=params['ord_sim'])
    if params.get('oper'):
        qs = qs.filter(id_sim__operator=params['oper'])
    if params.get('ord_st'):
        qs = qs.filter(order_status=params['ord_st'])
    return qs

def _orders_list_url_filter(params):
    query = {}
    if params.get('q'):
        query['q'] = params['q']
    if params.get('ord_name'):
        query['ord_name'] = params['ord_name']
    if params.get('ord_order'):
        query['ord_order'] = params['ord_order']
    if params.get('ord_sim'):
        query['ord_sim'] = params['ord_sim']
    if params.get('oper'):
        query['oper'] = params['oper']
    if params.get('ord_st'):
        query['ord_st'] = params['ord_st']
    if params.get('per_page') and params['per_page'] != ORDERS_LIST_DEFAULT_PER_PAGE:
        query['per_page'] = params['per_page']
    return f'&{urlencode(query)}' if query else ''

def _orders_list_redirect(params=None):
    url = reverse('orders_list')
    if not params:
        return redirect(url)
    query = _orders_list_url_filter(params)
    return redirect(f'{url}?{query[1:]}' if query else url)


# Order list
@login_required(login_url='/login/')
@has_permission_decorator('view_orders')
def orders_list(request):
    url_cdn = settings.URL_CDN
    link_esim_android = settings.LINK_ESIM_ANDROID
    link_esim_ios = settings.LINK_ESIM_IOS

    params = _orders_list_params(request)

    if request.method == 'POST' and 'up_status' in request.POST:
        ord_id = request.POST.getlist('ord_id')
        ord_s = request.POST.get('ord_status')
        id_user = request.user.id if request.user.is_authenticated else None

        if ord_s and ord_id:
            status = dict(Orders.order_status.field.choices).get(ord_s, ord_s)
            print(f"[VIEW] Enfileirando orders_up_status: ord_id={ord_id}, status={ord_s}, user={id_user}")
            orders_up_status.delay(ord_id, ord_s, id_user)
            messages.success(request, f'Atualizando {len(ord_id)} pedido(s) para status: {status}')
        else:
            print(f"[VIEW] Dados inválidos: ord_id={ord_id}, status={ord_s}")
            messages.error(request, 'Selecione pedidos e status antes de atualizar')

        return _orders_list_redirect(params)

    orders_base = Orders.objects.exclude(product='chamada-de-voz').order_by('-id')
    orders_l = _apply_orders_list_filters(orders_base, params)
    orders_count = orders_l.count()

    # Guarda só os filtros (leve) para o export montar o CSV sob demanda
    request.session['orders_list_filters'] = {
        'q': params['q'],
        'oper': params['oper'],
        'ord_st': params['ord_st'],
        'ord_name': params['ord_name'],
        'ord_order': params['ord_order'],
        'ord_sim': params['ord_sim'],
    }
    request.session.pop('orders_listing', None)

    status_counts = {
        row['order_status']: row['total']
        for row in Orders.objects.exclude(product='chamada-de-voz')
        .values('order_status')
        .annotate(total=Count('id'))
    }
    ord_st_list = [
        (code, label, status_counts.get(code, 0))
        for code, label in Orders.order_status.field.choices
    ]
    oper_list = Sims.operator.field.choices

    paginator = Paginator(orders_l.select_related('id_sim'), params['per_page'])
    orders = paginator.get_page(request.GET.get('page') or request.POST.get('page') or 1)
    url_filter = _orders_list_url_filter(params)

    context = {
        'url_cdn': url_cdn,
        'link_esim_android': link_esim_android,
        'link_esim_ios': link_esim_ios,
        'orders': orders,
        'ord_st_list': ord_st_list,
        'oper_list': oper_list,
        'url_filter': url_filter,
        'q': params['q'],
        'oper_f': params['oper'],
        'ord_st_f': params['ord_st'],
        'per_page': params['per_page'],
        'per_page_choices': ORDERS_LIST_PER_PAGE_CHOICES,
        'orders_count': orders_count,
    }
    return render(request, 'painel/orders/index.html', context)

@login_required(login_url='/login/')
def ord_details(request, order_id):
    
    data_d = {
        '500mb-dia': '500',
        '1gb': '1000',
        '2gb': '2000',
        'ilimitado': 'Ilimitado',
        }
    
    order = Orders.objects.get(pk=order_id)
    name = order.client
    sim = order.id_sim.sim if order.id_sim else ''
    data_day = data_d[order.data_day] if order.data_day else ''
    data_day_d = order.get_data_day_display() if order.data_day else ''
    operator = order.id_sim.operator if order.id_sim else ''
    product = order.get_product_display()
    mobile_data_f = '0.00'
    percent_used = 0
        
    if (operator == 'TI' or operator == 'TC') and sim != '':
        # Verificar consumo de dados TC
        mobile_data = ApiTC.mobileData(sim)
    elif operator == 'CM':
        # Verificar consumo de dados CM
        mobile_data = ApiCM.mobileData(sim)
    elif operator == 'CMHK':
        mobile_data = ApiCMHK.mobileData(sim)
    else:
        mobile_data = ''
    
    if mobile_data != '':
        mobile_data_f = f"{float(mobile_data):.2f}"
        
    print(f'Consumo de dados: {mobile_data} MB')
    
    # Calcular porcentagem de dados usados
    # data_day é o total (em MB ou 'Ilimitado'), mobile_data é o usado (em MB)
    if data_day and data_day != 'Ilimitado':
        try:
            total_data = float(data_day)
            used_data = float(mobile_data)
            percent_used = (used_data / total_data) * 100
            percent_used = round(percent_used, 2)
        except Exception:
            percent_used = 0
    else:
        percent_used = 0  # Não calcula para ilimitado ou dados inválidos        
    
    operator_label = ''
    if order.id_sim:
        operator_label = order.id_sim.get_operator_display()

    data = {
        'name': name,
        'sim': sim,
        'data_day': data_day,
        'data_day_d': data_day_d,
        'operator': operator_label or operator,
        'product': product,
        'mobile_data': mobile_data_f,
        'percent_used': percent_used,
        }

    return JsonResponse(data)


@login_required(login_url='/login/')
@has_permission_decorator('edit_orders')
def ord_edit(request,id):
    if request.method == 'GET':
            
        order = Orders.objects.get(pk=id)
        ord_status = Orders.order_status.field.choices
        ord_product = sorted(Orders.product.field.choices, key=lambda c: c[1].lower())
        ord_data_day = sorted(Orders.data_day.field.choices, key=lambda c: c[1].lower())
        ord_operators = sorted(Sims.operator.field.choices, key=lambda c: c[1].lower())

        days = list(range(1, 31))
        
        context = {
            'order': order,
            'ord_status': ord_status,
            'ord_product': ord_product,
            'ord_data_day': ord_data_day,
            'ord_operators': ord_operators,
            'ord_days': days,
        }
        return render(request, 'painel/orders/edit.html', context)
        
    if request.method == 'POST':
        
        print('>>>>>>>>>> EDITAR PEDIDO')
        
        global msg_info
        msg_info = []
        global msg_error
        msg_error = []
        global id_sim
        id_sim = ''
        global ord_st
        ord_st = ''
        global update_store
        update_store = {}
        
        
        order = Orders.objects.get(pk=id)
        order_id = order.order_id
        order_status = order.order_status
        try: order_sim = order.id_sim.sim
        except: order_sim = ''
        try: sim_id = int(order.id_sim.id)
        except: sim_id = ''
        qrcode = ''
        up_plan = False
        days = request.POST.get('days')
        product = request.POST.get('product')
        data_day = request.POST.get('data_day')
        type_sim = request.POST.get('type_sim')
        operator = request.POST.get('operator')
        sim = request.POST.get('sim')
        activation_date = request.POST.get('activation_date')
        email = request.POST.get('email')
        cell_imei = request.POST.get('cell_imei')
        cell_eid = request.POST.get('cell_eid')
        tracking = request.POST.get('tracking')
        ord_st = request.POST.get('ord_st_f')
        ord_note = request.POST.get('ord_note')
        up_oper = request.POST.get('upOper')
        esim_v = None
                
        # Update SIM in Order and update SIM
        def updateSIM():
            if sim_id:  # ADICIONAR VERIFICAÇÃO
                # Update SIM
                sim_put = Sims.objects.get(pk=sim_id)            
                sim_put.sim_status = 'TC'
                sim_put.save()
                # Delete SIM in Order
                order_put = Orders.objects.get(pk=order.id)
                order_put.id_sim_id = None  # CORRIGIR: usar None em vez de ''
                order_put.save()
            else:
                print("Aviso: Tentativa de atualizar SIM, mas sim_id está vazio")

        # Verificar Usuário
        try:
            id_user = User.objects.get(pk=request.user.id)
            type_note_i = 'P'
        except:
            id_user = None
            type_note_i = 'S'

        # Notes
        def addNote(t_note):
            add_sim = Notes( 
                id_item = Orders.objects.get(pk=order.id),
                id_user = id_user,
                note = t_note,
                type_note = type_note_i,
            )
            add_sim.save()
            
        # Insert SIM in Order
        def insertSIM(ord_st=None):
            nonlocal qrcode
            sim_up = Sims.objects.filter(sim_status='DS', type_sim=type_sim, operator=operator).first()
            if sim_up:
                sim_put = Sims.objects.get(pk=sim_up.id)
                if order_sim != '':
                    # Update SIM
                    updateSIM()
                sim_put.sim_status = 'AT'
                sim_put.save()
                
                qrcode = sim_up.link if sim_up.link else ""
                
                if type_sim == 'esim': 
                    ord_st = 'AA'
                else: ord_st = ord_st
                
                order_put = Orders.objects.get(pk=order.id)
                order_put.id_sim_id = sim_put.id
                order_put.order_status = ord_st
                order_put.save()
            else:       
                msg_error.append(f'Não há estoque de {operator} - {type_sim} no sistema')

        # Se SIM preenchico
        if sim:
            if order_sim != '':
                # Alterar status do SIM no sistema e no site
                updateSIM()
            
            sims_all = Sims.objects.all().filter(sim=sim)
            if sims_all:
                # Update order
                sim_id = sims_all[0].id
                qrcode = sims_all[0].link
                sims_put = Sims.objects.get(pk=sim_id)
                sims_put.sim_status = 'AT'
                sims_put.save()
                order_put = Orders.objects.get(pk=order.id)
                order_put.id_sim_id = sim_id
                order_put.save()
                up_plan = True # verificação para nota
            else:
                # Save SIMs - Insert Stock
                add_sim = Sims( 
                    sim = sim,
                    type_sim = type_sim,
                    operator = operator,
                    sim_status = 'AT',
                )
                add_sim.save()
            
                # Update order
                order_put = order
                order_put.id_sim_id = add_sim.id
                order_put.save()
                up_plan = True # verificação para nota
            
            # Gravar SIM e QRCode no site
            try:
                sim = order.id_sim.sim
                qrcode = order.id_sim.link if order.id_sim.link else None
            except:
                sim = ''
                qrcode = None
            
            # SIM Notes
            if sim != '':
                addNote(f'Alteração de {order_sim} para {sim}')
            
        else:
            # Troca de SIM
            if order_sim != '' and order.id_sim:
                if order.id_sim.operator != operator or order.id_sim.type_sim != type_sim or up_oper != None:
                    updateSIM()
                    insertSIM(ord_st)
                    up_plan = True # verificação para nota
                    
                    # Update SIM
                    esim_v = True             
            else:
                if operator != None and type_sim != None:
                    if product != 'chip-internacional-europa' and type_sim != 'esim':
                        insertSIM(ord_st)
                        up_plan = True # verificação para nota
            
            # Gravar SIM e QRCode no site
            if order.item_id_store and order.id_sim:
                sim = order.id_sim.sim
                qrcode = order.id_sim.link if order.id_sim.link else None

        # Update Order
        if activation_date == '':
            activation_date = order.activation_date
        else:
            voice = VoiceCalls.objects.filter(id_item=order.id).first()
            if voice:
                voice.activation_date = activation_date
                voice.save()
            addNote(f'Data alterada de {DateFormats.dateDMA(str(order.activation_date))} para {DateFormats.dateDMA(str(activation_date))}')
        if email == '':
            email = order.email
        if not product or product == '':
            product = order.product
        if not data_day or data_day == '':
            data_day = order.data_day
        if not days or days == '':
            days = order.days
                
        order_put = Orders.objects.get(pk=order.id)
        order_put.days = days
        order_put.product = product
        order_put.data_day = data_day
        order_put.activation_date = activation_date
        order_put.email = email
        order_put.cell_imei = cell_imei
        order_put.cell_eid = cell_eid
        order_put.tracking = tracking
        order_put.order_status = ord_st
        order_put.type_sim = type_sim
        order_put.oper_sim = operator
        order_put.save()
        
        # Save Notes
        if ord_note:
            addNote(ord_note)

        # Plan Notes
        if up_plan:  # Agora up_plan está inicializado
            addNote(f'Plano alterado')
                 
        # Status Notes
        if ord_st != order_status:
            # Alterar status
            # Status sis : Status Loja            
            user_name = request.user.id
            ord_s_prev = order_status
            
            orders_up_status(order.id, ord_st,user_name, ord_s_prev) 
                        
            # Enviar email
            if ord_st == 'CN' and type_sim == 'sim':
                send_email_sims(id=order_id)
                
                addNote(f'E-mail enviado com sucesso!')
                messages.success(request,'E-mail enviado com sucesso!')
            elif ord_st == 'ET':
                send_email_sims(id=order_id, troca=True)
                
                addNote(f'E-mail de troca enviado com sucesso!')
                messages.success(request,'E-mail enviado com sucesso!')
                # alterar status do pedido
                order_put = Orders.objects.get(pk=order.id)
                order_put.order_status = 'AA'
                order_put.save()
                addNote(f'Status do pedido alterado para Ativado!')
                messages.success(request,'Status do pedido alterado para Ativado!')

        if order.id_sim and (order.id_sim.operator == 'TI' or order.id_sim.operator == 'TC') and ord_st == 'DE':
            print('----------------- Alterar/desativar TC/TI -----------------')
            simDeactivateTC(id=order.id)

        # Atualizar site
        try:
            UpdateStore.upStore(
                order_id = order_id,
                item_id_store = order.item_id_store if order.item_id_store else None,
                _data_ativacao = str(activation_date) if activation_date else None,
                _sim = sim if sim else None,
                _qrcode = qrcode if qrcode else None,
                _status = ord_st if ord_st else None,
                status_g = ord_st if ord_st else None,
            )
        except Exception as e:
            print(f">>>>>>>>>> ERRO ao atualizar site: {e}")
                
        for msg_e in msg_error:
            messages.error(request,msg_e)
        for msg_o in msg_info:
            messages.info(request,msg_o)
        messages.success(request,f'Pedido {order.order_id} atualizado com sucesso!')
        return redirect('orders_list')


@login_required(login_url='/login/')
@has_permission_decorator('export_orders')
def ord_export(request):
    list_status = dict(Orders.order_status.field.choices)
    list_oper = dict(Sims.operator.field.choices)

    filters = request.session.get('orders_list_filters')
    if filters is None and request.session.get('orders_listing'):
        # Compatibilidade com sessão antiga (lista completa em memória)
        orders_rows = request.session.get('orders_listing')
    elif filters is not None:
        qs = _apply_orders_list_filters(
            Orders.objects.exclude(product='chamada-de-voz').order_by('-id'),
            filters,
        )
        orders_rows = []
        for row in qs.values(
            'item_id', 'client', 'id_sim__sim', 'id_sim__operator',
            'product', 'data_day', 'countries', 'calls', 'days',
            'activation_date', 'order_status',
        ):
            ad = row.get('activation_date')
            days_val = row.get('days') or 0
            ret = (ad + timedelta(days=days_val - 1)) if (ad and days_val) else None
            orders_rows.append({
                **row,
                'activation_date': ad.isoformat() if ad else None,
                'return_date': ret.isoformat() if ret else None,
            })
    else:
        messages.error(
            request,
            'Nenhum dado disponível para exportação. Abra a lista de pedidos antes de exportar.',
        )
        return redirect('orders_list')

    print(f'>>>>>>>>>>>>>>>>>>>>>< Exportando {len(orders_rows)} pedidos')

    data = [
        ['Pedido', 'Cliente', '(e)SIM', 'Operadora', 'Produto', 'Países', 'Voz', 'Dias', 'Data Aivação', 'Data Término', 'Status']
    ]

    for ord in orders_rows:
        if ord['id_sim__operator']:
            ord_operator = list_oper.get(ord['id_sim__operator'], '')
        else:
            ord_operator = ''
        ord_data = '' if ord.get('data_day') == 'Ilimitado' else (ord.get('data_day') or '')
        ord_product = f"{ord['product']} {ord_data}".strip()
        ord_date_start = DateFormats.dateDMA(str(ord['activation_date']))
        ord_date_end = DateFormats.dateDMA(str(ord['return_date']))
        ord_calls = 'SIM' if ord['calls'] else ''
        ord_countries = 'SIM' if ord['countries'] else ''
        ord_status = list_status.get(ord['order_status'], ord['order_status'])
        data.append([
            ord['item_id'], ord['client'], ord['id_sim__sim'], ord_operator, ord_product,
            ord_countries, ord_calls, ord['days'], ord_date_start, ord_date_end, ord_status,
        ])

    data_atual = date.today()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="Ativacoes-{data_atual}.csv"'
    writer = csv.writer(response)
    for row in data:
        writer.writerow(row)
    return response 


@login_required(login_url='/login/')
@has_permission_decorator('export_activations')
def ord_export_op(request):
    
    sims_op = Sims.operator.field.choices
    context= {
        'sims_op': sims_op,
    } 
    
    if request.method == 'POST':
        
        ord_op_f = request.POST.get('ord_op_f')
        
        orders_all = Orders.objects.all().order_by('id').filter(order_status='AA')
        
        if ord_op_f != 'op_all':
            orders_all = orders_all.filter(id_sim_id__operator__icontains=ord_op_f)
            
        # Crie uma lista com os dados que você deseja exportar para o CSV
        data = [
            ['Data Compra', 'Pedido', '(e)SIM', 'EID', 'IMEI','Plano', 'Dias', 'Data Aivação', 'Operadora', 'Voz', 'Países']
        ]
        
        ord_prod_list = {
            'chip-internacional-eua': 'T-Mobile',
            'chip-internacional-eua-e-canada': 'USA E CANADA',
            'chip-internacional-eua-canada-e-mexico': 'USA/CAN/MEX',
            'chip-internacional-europa': 'EUROPA',
            'chip-internacional-global': 'GLOBAL PREMIUM',
        }
        
        for ord in orders_all:
            ord_date = DateFormats.dateDMA(str(ord.order_date))
            if ord.data_day != 'ilimitado': 
                ord_data = ord.get_data_day_display()
            else: ord_data = ''
            ord_product = f'{ord_prod_list[ord.product]} {ord_data}'
            ord_date_act = DateFormats.dateDMA(str(ord.activation_date))
            if ord.id_sim:
                ord_op = ord.id_sim.get_operator_display()
                ord_sim = ord.id_sim.sim
            else:
                ord_op = '-'
                ord_sim = '-'
            if ord.calls == True:
                ord_calls = 'SIM'
            else: ord_calls = ''
            if ord.countries == True:
                ord_countries = 'SIM'
            else: ord_countries = ''
            data.append([ord_date,ord.item_id,ord_sim,ord.cell_eid,ord.cell_imei,ord_product,ord.days,ord_date_act,ord_op,ord_calls,ord_countries])

        data_atual = date.today()
        
        # Crie um objeto CSVWriter para escrever os dados no formato CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="Ativacoes-{data_atual}-{ord_op_f}.csv"'
        writer = csv.writer(response)

        # Escreva os dados no objeto CSVWriter
        for row in data:
            writer.writerow(row)

        messages.success(request, 'Arquivo CSV baixado com sucesso!')
        return response 
    
    return render(request, 'painel/orders/export_op.html', context)


@login_required(login_url='/login/')
@has_permission_decorator('list_activations')
def orders_activations(request):
    url_filter = ''
    activGoing_f = None
    activGoing_1 = None
    activGoing_2 = None
    activReturn_f = None
    activReturn_1 = None
    activReturn_2 = None
    oper_f = None
    ord_st_f = None
    ord_planos_f = None

    fields_df = ['id', 'item_id','client', 'id_sim__sim', 'id_sim__link', 'id_sim__type_sim', 'id_sim__operator', 'product', 'data_day', 'calls', 'countries', 'days', 'cell_mod', 'cell_eid', 'cell_imei', 'activation_date', 'order_status']

    product_choice_dict = dict(Orders.product.field.choices)
    data_choice_dict = dict(Orders.data_day.field.choices)
    status_choice_dict = dict(Orders.order_status.field.choices)
    
    today = datetime.now()
    days60 = today - timedelta(days=60)
    
    orders_all = Orders.objects.filter(activation_date__gte=days60).order_by('activation_date')
    
    orders_df = pd.DataFrame((orders_all.values(*fields_df)))
    
    orders_df['product_code'] = orders_df['product']
    orders_df['product'] = orders_df['product'].map(product_choice_dict)
    orders_df['data_day'] = orders_df['data_day'].map(data_choice_dict)
    orders_df['activation_date'] = pd.to_datetime(orders_df['activation_date'])
    orders_df['return_date'] = orders_df['activation_date'] + pd.to_timedelta(orders_df['days'], unit='d') - pd.to_timedelta(1, unit='d')
    
    orders_l = orders_df

    # Obter parâmetros de filtro (tanto GET quanto POST)
    if request.method == 'GET':
        if request.GET.get('activGoing_1'): activGoing_1 = request.GET.get('activGoing_1')
        if request.GET.get('activGoing_2'): activGoing_2 = request.GET.get('activGoing_2')
        if request.GET.get('activReturn_1'): activReturn_1 = request.GET.get('activReturn_1')
        if request.GET.get('activReturn_2'): activReturn_2 = request.GET.get('activReturn_2')
        if request.GET.get('oper'): oper_f = request.GET.get('oper')
        if request.GET.get('ord_st'): ord_st_f = request.GET.get('ord_st')
        if request.GET.get('ord_planos'): ord_planos_f = request.GET.get('ord_planos')

    if request.method == 'POST':
        if request.POST.get('activGoing_f'): activGoing_f = request.POST.get('activGoing_f')
        if request.POST.get('activReturn_f') : activReturn_f = request.POST.get('activReturn_f')
        if request.POST.get('oper_f'): oper_f = request.POST.get('oper_f')
        if request.POST.get('ord_st_f'): ord_st_f = request.POST.get('ord_st_f')
        if request.POST.get('ord_planos_f'): ord_planos_f = request.POST.get('ord_planos_f')
           
        if 'up_status' in request.POST:
            ord_id = request.POST.getlist('ord_id')
            ord_s = request.POST.get('ord_status')
            
            # Validações completas
            if not ord_id or not ord_s or ord_s == '':
                messages.error(request, 'Dados incompletos para atualização de status')
                return redirect('orders_activations')
            
            # Verificar autenticação
            if not request.user.is_authenticated:
                messages.error(request, 'Usuário não autenticado')
                return redirect('orders_activations')
            
            id_user = request.user.id
            
            # Log para debug
            print(f">>>>>>>>>> ATUALIZAÇÃO EM MASSA (ACTIVATIONS)")
            print(f"Pedidos: {ord_id}, Status: {ord_s}, Usuário: {id_user}")
            
            try:
                orders_up_status.delay(ord_id, ord_s, id_user)
                messages.success(request, f'Atualizando {len(ord_id)} pedidos para status: {ord_s}')
            except Exception as e:
                messages.error(request, f'Erro ao iniciar atualização: {str(e)}')
            
            return redirect('orders_activations')                

    # Aplicar filtros baseados nos parâmetros GET (para paginação)
    if activGoing_1 and activGoing_2:
        orders_l = orders_l[(orders_l['activation_date'] >= activGoing_1) & (orders_l['activation_date'] <= activGoing_2)]
        url_filter += f"&activGoing_1={activGoing_1}&activGoing_2={activGoing_2}"
    elif activGoing_1:
        orders_l = orders_l[(orders_l['activation_date'] == activGoing_1)]
        url_filter += f"&activGoing_1={activGoing_1}"  
        
    if activReturn_1 and activReturn_2:
        orders_l = orders_l[(orders_l['return_date'] >= activReturn_1) & (orders_l['return_date'] <= activReturn_2)]
        url_filter += f"&activReturn_1={activReturn_1}&activReturn_2={activReturn_2}"
    elif activReturn_1:
        orders_l = orders_l[(orders_l['return_date'] == activReturn_1)]
        url_filter += f"&activReturn_1={activReturn_1}"
        
    if oper_f:
        orders_l = orders_l[(orders_l['id_sim__operator'] == oper_f)]
        url_filter += f"&oper={oper_f}"
        
    if ord_st_f:
        orders_l = orders_l[(orders_l['order_status'] == ord_st_f)]
        url_filter += f"&ord_st={ord_st_f}"
        
    if ord_planos_f:
        orders_l = orders_l[(orders_l['product_code'] == ord_planos_f)]
        url_filter += f"&ord_planos={ord_planos_f}"

    # Aplicar filtros para POST (formulário)
    if request.method == 'POST':
        if activGoing_f is not None:
            activGoing = [item.strip() for item in activGoing_f.split('-')]
            activGoing_1 = DateFormats.dateF(activGoing[0])
            try: 
                activGoing_2 = DateFormats.dateF(activGoing[1])
                orders_l = orders_l[(orders_l['activation_date'] >= activGoing_1) & (orders_l['activation_date'] <= activGoing_2)]
                url_filter += f"&activGoing_1={activGoing_1}&activGoing_2={activGoing_2}"
            except:
                orders_l = orders_l[(orders_l['activation_date'] == activGoing_1)]
                url_filter += f"&activGoing_1={activGoing_1}"  
                
        if activReturn_f is not None:
            activReturn = [item.strip() for item in activReturn_f.split('-')]
            activReturn_1 = DateFormats.dateF(activReturn[0])
            try: 
                activReturn_2 = DateFormats.dateF(activReturn[1])
                orders_l = orders_l[(orders_l['return_date'] >= activReturn_1) & (orders_l['return_date'] <= activReturn_2)]
                url_filter += f"&activReturn_1={activReturn_1}&activReturn_2={activReturn_2}"
            except:
                orders_l = orders_l[(orders_l['return_date'] == activReturn_1)]
                url_filter += f"&activReturn_1={activReturn_1}"
        if ord_planos_f:
            orders_l = orders_l[(orders_l['product_code'] == ord_planos_f)]
            url_filter += f"&ord_planos={ord_planos_f}"

    # Total de registro
    orders_count = int(orders_l.shape[0])
    
    sims = Sims.objects.all()
    oper_list = Sims.operator.field.choices
    ord_status = Orders.order_status.field.choices
    plan_list = sorted(Orders.product.field.choices, key=lambda c: c[1].lower())

    # Listar status dos pedidos
    ord_st_list = []
    for ord_s in ord_status:
        ord = len(orders_l[orders_l['order_status'] == ord_s[0]])
        ord_st_list.append((ord_s[0],ord_s[1],ord))
        
    # Listar ativações
    today = datetime.now().date()
    activList = orders_l[orders_l['activation_date'].dt.date > today]
    activList = activList.groupby(['id_sim__operator']).size().reset_index(name='countActiv')
    countActivAll = countActivAll = activList['countActiv'].sum()
    try: countActivTM = activList[activList['id_sim__operator'] == 'TM']['countActiv'].values[0]
    except: countActivTM = 0
    try: countActivCM = activList[activList['id_sim__operator'] == 'CM']['countActiv'].values[0]
    except: countActivCM = 0
    try: countActivTC = activList[activList['id_sim__operator'] == 'TC']['countActiv'].values[0]
    except: countActivTC = 0
    try: countActivTI = activList[activList['id_sim__operator'] == 'TI']['countActiv'].values[0]
    except: countActivTI = 0
    try: countActivMS = activList[activList['id_sim__operator'] == 'MV']['countActiv'].values[0]
    except: countActivMS = 0

    # Save in session
    orders_act = orders_l.copy()
    orders_act['activation_date'] = orders_act['activation_date'].astype(str)
    orders_act['return_date'] = orders_act['return_date'].astype(str)
    orders_act = orders_act.to_dict(orient='records')
    request.session['orders_listing'] = orders_act
    # List
    orders_l = orders_l.to_dict('records')
  
    
    # Paginação
    paginator = Paginator(orders_l, 100)
    page = request.GET.get('page', 1)
    orders = paginator.get_page(page)
    
    context = {
        'orders_l': orders_l,
        'orders': orders,
        'sims': sims,
        'ord_st_list': ord_st_list,
        'plan_list': plan_list,
        'oper_list': oper_list,
        'url_filter': url_filter,
        'status_choice_dict': status_choice_dict,
        'countActivAll': countActivAll,
        'countActivTM': countActivTM,
        'countActivCM': countActivCM,
        'countActivTC': countActivTC,
        'countActivTI': countActivTI,
        'countActivMS': countActivMS,
        'activGoing_1': activGoing_1,
        'activGoing_2': activGoing_2,
        'activReturn_1': activReturn_1,
        'activReturn_2': activReturn_2,
        'oper_f': oper_f,
        'ord_st_f': ord_st_f,
        'ord_planos_f': ord_planos_f,
        'orders_count': orders_count,
    }
    return render(request, 'painel/orders/activations.html', context)


@login_required(login_url='/login/')
def update_status(request):
    # Atualizar status dos pedidos
    update_st.delay()
    messages.success(request, 'Processando atualização de status... Aguarde alguns minutos e atualize a página de pedidos')
    return HttpResponse('Atualizando status!')


@login_required(login_url='/login/')
@has_permission_decorator('export_activations')
def export_client_progress(request):
    export_id = request.GET.get('export_id')
    if not export_id:
        return JsonResponse({'status': 'error', 'message': 'ID de exportação inválido.'}, status=400)
    return JsonResponse(ExportClients.process_next_page(export_id))


@login_required(login_url='/login/')
@has_permission_decorator('export_activations')
def export_client_download(request):
    export_id = request.GET.get('export_id')
    if not export_id:
        return HttpResponse('ID de exportação inválido.', status=400)

    response = ExportClients.build_download_response(export_id)
    if response is None:
        return HttpResponse('Arquivo não encontrado ou exportação ainda em andamento.', status=404)
    return response


@login_required(login_url='/login/')
@has_permission_decorator('export_activations')
def exportClient(request):
    if request.method == 'POST':
        export_id = ExportClients.start()
        return JsonResponse({'export_id': export_id})

    return render(request, 'painel/orders/export_clients.html')
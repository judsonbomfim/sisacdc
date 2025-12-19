from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.sims.models import Sims
from apps.orders.models import Orders
from apps.voice_calls.models import VoiceCalls
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict


# Create your views here.
@login_required(login_url='/login/')
def index(request):
    # Dates
    today = datetime.now()
    dateDay = today.date()
    
    dateTomorrow = dateDay + timedelta(days=1)
    dateYesterday = dateDay - timedelta(days=1)
    dateWeek = dateDay - timedelta(days=7)
    dateMonth = dateDay - timedelta(days=30)
    dateYear = dateDay - timedelta(days=365)
    
    # Ativações pendentes
    orders_pending = Orders.objects.filter(
        activation_date__lte=dateDay
    ).exclude(
        order_status__in=['AT', 'CC', 'CN', 'DE', 'DA', 'ED', 'PV', 'RB', 'RE', 'RC']
    ).order_by('activation_date') 
    
    voices_pending = VoiceCalls.objects.filter(
        activation_date__lte=dateDay
    ).exclude(
        call_status__in=['AT', 'CC', 'CN', 'DS']
    ).order_by('activation_date') 
    
    # ACTIVATIONS
    activationOrders = Orders.objects.filter(activation_date=dateTomorrow)
    activationTomorrow = activationOrders.count()    
    activ_values = activationOrders.values_list('id_sim__operator', flat=True)
    operator_counts = Counter(activ_values)

    countActivTM = operator_counts.get('TM', 0)
    countActivCM = operator_counts.get('CM', 0)
    countActivTC = operator_counts.get('TC', 0)
    countActivTI = operator_counts.get('TI', 0)
    countActivMS = operator_counts.get('MS', 0)
    
    # Queries
    simsAll = Sims.objects.all()
    ordersWeek = Orders.objects.filter(order_date__range=(dateWeek, dateDay))
    ordersMonth = Orders.objects.filter(order_date__range=(dateMonth, dateDay))
    ordersYear = Orders.objects.filter(order_date__range=(dateYear, dateDay))     
    
    fields = ['order_id', 'order_date', 'id_sim__type_sim', 'id_sim__operator']

    def process_orders(orders_qs):
        processed = []
        for order in orders_qs.values(*fields):
            processed.append({
                'order_id': order['order_id'],
                'order_date': order['order_date'].date(),
                'type_sim': order['id_sim__type_sim'],
                'operator': order['id_sim__operator'],
            })
        return processed

    week_orders = process_orders(ordersWeek)
    month_orders = process_orders(ordersMonth)
    
    year_orders = []
    for order in ordersYear.values(*fields):
        order_date = order['order_date'].date()
        year_orders.append({
            'order_id': order['order_id'],
            'order_date': order_date,
            'month': order_date.replace(day=1),
            'type_sim': order['id_sim__type_sim'],
            'operator': order['id_sim__operator'],
        })

    # SALES
    # --- Week
    unique_week_sales = {sale['order_id']: sale for sale in week_orders}.values()
    sales_by_date_week = defaultdict(int)
    for sale in unique_week_sales:
        sales_by_date_week[sale['order_date']] += 1
    sorted_sales_week = sorted(sales_by_date_week.items())
    
    weekSalesDates = json.dumps([d.strftime('%Y-%m-%d') for d, v in sorted_sales_week])
    weekSalesValues = json.dumps([v for d, v in sorted_sales_week])
    
    # --- Month
    unique_month_sales = {sale['order_id']: sale for sale in month_orders}.values()
    sales_by_date_month = defaultdict(int)
    for sale in unique_month_sales:
        sales_by_date_month[sale['order_date']] += 1
    sorted_sales_month = sorted(sales_by_date_month.items())

    monthSalesDates = json.dumps([d.strftime('%Y-%m-%d') for d, v in sorted_sales_month])
    monthSalesValues = json.dumps([v for d, v in sorted_sales_month])

    # --- Year
    unique_year_sales = {sale['order_id']: sale for sale in year_orders}.values()
    sales_by_month_year = defaultdict(int)
    for sale in unique_year_sales:
        sales_by_month_year[sale['month']] += 1
    
    # --- Generate all dates for the ranges
    all_week_dates = [dateWeek + timedelta(days=i) for i in range((dateDay - dateWeek).days + 1)]
    all_month_dates = [dateMonth + timedelta(days=i) for i in range((dateDay - dateMonth).days + 1)]
    
    # Generate all months for the year range
    all_year_months = []
    current_month = dateYear.replace(day=1)
    while current_month <= dateDay.replace(day=1):
        all_year_months.append(current_month)
        # Move to the next month
        next_month = current_month.replace(day=28) + timedelta(days=4)  # Go to end of month, then add 4 days
        current_month = next_month.replace(day=1)

    # --- Sales processing using all dates
    sales_by_date_week = {d: sales_by_date_week.get(d, 0) for d in all_week_dates}
    sorted_sales_week = sorted(sales_by_date_week.items())

    sales_by_date_month = {d: sales_by_date_month.get(d, 0) for d in all_month_dates}
    sorted_sales_month = sorted(sales_by_date_month.items())

    sales_by_month_year = {m: sales_by_month_year.get(m, 0) for m in all_year_months}
    sorted_sales_year = sorted(sales_by_month_year.items())

    weekSalesDates = json.dumps([d.strftime('%Y-%m-%d') for d, v in sorted_sales_week])
    weekSalesValues = json.dumps([v for d, v in sorted_sales_week])

    monthSalesDates = json.dumps([d.strftime('%Y-%m-%d') for d, v in sorted_sales_month])
    monthSalesValues = json.dumps([v for d, v in sorted_sales_month])

    yearSalesDates = json.dumps([d.strftime('%Y-%m') for d, v in sorted_sales_year])
    yearSalesValues = json.dumps([v for d, v in sorted_sales_year])

    # SIMs
    # --- Week  
    sims_by_date_type_week = defaultdict(lambda: defaultdict(int))
    for order in week_orders:
        sims_by_date_type_week[order['order_date']][order['type_sim']] += 1
    
    weekSimsDates = json.dumps([d.strftime('%Y-%m-%d') for d in all_week_dates])
    weekSimsValuesS = json.dumps([sims_by_date_type_week[d].get('esim', 0) for d in all_week_dates])
    weekSimsValuesE = json.dumps([sims_by_date_type_week[d].get('sim', 0) for d in all_week_dates])

    # --- Month
    sims_by_date_type_month = defaultdict(lambda: defaultdict(int))
    for order in month_orders:
        sims_by_date_type_month[order['order_date']][order['type_sim']] += 1

    monthSimsDates = json.dumps([d.strftime('%Y-%m-%d') for d in all_month_dates])
    monthSimsValuesS = json.dumps([sims_by_date_type_month[d].get('esim', 0) for d in all_month_dates])
    monthSimsValuesE = json.dumps([sims_by_date_type_month[d].get('sim', 0) for d in all_month_dates])

    # --- Year
    sims_by_month_type_year = defaultdict(lambda: defaultdict(int))
    for order in year_orders:
        sims_by_month_type_year[order['month']][order['type_sim']] += 1

    yearSimsDates = json.dumps([m.strftime('%Y-%m') for m in all_year_months])
    yearSimsValuesS = json.dumps([sims_by_month_type_year[m].get('esim', 0) for m in all_year_months])
    yearSimsValuesE = json.dumps([sims_by_month_type_year[m].get('sim', 0) for m in all_year_months])

    # OPERATOR
    # --- Week
    oper_by_date_week = defaultdict(lambda: defaultdict(int))
    for order in week_orders:
        oper_by_date_week[order['order_date']][order['operator']] += 1

    weekOperDates = json.dumps([d.strftime('%Y-%m-%d') for d in all_week_dates])
    weekOperValuesTM = json.dumps([oper_by_date_week[d].get('TM', 0) for d in all_week_dates])
    weekOperValuesCM = json.dumps([oper_by_date_week[d].get('CM', 0) for d in all_week_dates])
    weekOperValuesTC = json.dumps([oper_by_date_week[d].get('TC', 0) for d in all_week_dates])
    weekOperValuesTI = json.dumps([oper_by_date_week[d].get('TI', 0) for d in all_week_dates])

    # --- Month
    oper_by_date_month = defaultdict(lambda: defaultdict(int))
    for order in month_orders:
        oper_by_date_month[order['order_date']][order['operator']] += 1

    monthOperDates = json.dumps([d.strftime('%Y-%m-%d') for d in all_month_dates])
    monthOperValuesTM = json.dumps([oper_by_date_month[d].get('TM', 0) for d in all_month_dates])
    monthOperValuesCM = json.dumps([oper_by_date_month[d].get('CM', 0) for d in all_month_dates])
    monthOperValuesTC = json.dumps([oper_by_date_month[d].get('TC', 0) for d in all_month_dates])
    monthOperValuesTI = json.dumps([oper_by_date_month[d].get('TI', 0) for d in all_month_dates])

    # --- Year
    oper_by_month_year = defaultdict(lambda: defaultdict(int))
    for order in year_orders:
        oper_by_month_year[order['month']][order['operator']] += 1

    yearOperDates = json.dumps([m.strftime('%Y-%m') for m in all_year_months])
    yearOperValuesTM = json.dumps([oper_by_month_year[m].get('TM', 0) for m in all_year_months])
    yearOperValuesCM = json.dumps([oper_by_month_year[m].get('CM', 0) for m in all_year_months])
    yearOperValuesTC = json.dumps([oper_by_month_year[m].get('TC', 0) for m in all_year_months])
    yearOperValuesTI = json.dumps([oper_by_month_year[m].get('TI', 0) for m in all_year_months])

    # Verificar estoque de operadoras
    sim_tm = simsAll.filter(sim_status='DS',operator='TM', type_sim='sim').count()
    esim_tm = simsAll.filter(sim_status='DS',operator='TM', type_sim='esim').count()
    sim_cm = simsAll.filter(sim_status='DS',operator='CM', type_sim='sim').count()
    esim_cm = simsAll.filter(sim_status='DS',operator='CM', type_sim='esim').count()
    sim_tc = simsAll.filter(sim_status='DS',operator='TC', type_sim='sim').count()
    esim_tc = simsAll.filter(sim_status='DS',operator='TC', type_sim='esim').count()
    sim_ti = simsAll.filter(sim_status='DS',operator='TI', type_sim='sim').count()
    esim_ti = simsAll.filter(sim_status='DS',operator='TI', type_sim='esim').count()
    sim_ms = simsAll.filter(sim_status='DS',operator='MS', type_sim='sim').count()
    esim_ms = simsAll.filter(sim_status='DS',operator='MS', type_sim='esim').count()

    context= {
        'sims': simsAll,
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
        'dateDay': dateDay,
        'dateYesterday': dateYesterday,
        'dateWeek': dateWeek,
        'dateMonth': dateMonth,
        'dateYear': dateYear,
        'orders_pending': orders_pending,
        'voices_pending': voices_pending,
        'activationTomorrow': activationTomorrow,
        'countActivTM': countActivTM,
        'countActivCM': countActivCM,
        'countActivTC': countActivTC,
        'countActivTI': countActivTI,
        'countActivMS': countActivMS,
        'weekSalesDates': weekSalesDates,
        'weekSalesValues': weekSalesValues,
        'weekSimsDates': weekSimsDates,
        'weekSimsValuesS': weekSimsValuesS,
        'weekSimsValuesE': weekSimsValuesE,        
        'weekOperDates': weekOperDates,
        'weekOperValuesTM': weekOperValuesTM,
        'weekOperValuesCM': weekOperValuesCM,
        'weekOperValuesTC': weekOperValuesTC,
        'weekOperValuesTI': weekOperValuesTI,
        'monthSalesDates': monthSalesDates,
        'monthSalesValues': monthSalesValues,
        'monthSimsDates': monthSimsDates,
        'monthSimsValuesS': monthSimsValuesS,
        'monthSimsValuesE': monthSimsValuesE,
        'monthOperDates': monthOperDates,
        'monthOperValuesTM': monthOperValuesTM,
        'monthOperValuesCM': monthOperValuesCM,
        'monthOperValuesTC': monthOperValuesTC,
        'monthOperValuesTI': monthOperValuesTI,
        'yearSalesDates': yearSalesDates,
        'yearSalesValues': yearSalesValues,
        'yearSimsDates': yearSimsDates,
        'yearSimsValuesS': yearSimsValuesS,
        'yearSimsValuesE': yearSimsValuesE,
        'yearOperDates': yearOperDates,
        'yearOperValuesTM': yearOperValuesTM,
        'yearOperValuesCM': yearOperValuesCM,
        'yearOperValuesTC': yearOperValuesTC,      
        'yearOperValuesTI': yearOperValuesTI,      
    }
    
    return render(request, 'painel/dashboard/index.html', context)


@login_required(login_url='/login/')
def clear_cache(request):
    from django.core.cache import cache
    cache.clear()
    return HttpResponse("Cache cleared")
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.sims.models import Sims
from apps.orders.models import Orders
import json
from datetime import datetime, timedelta
import pandas as pd
import locale

# Definir o locale para português
locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')

# Create your views here.
@login_required(login_url='/login/')
def index(request):
    # Dates
    today = datetime.now()
    dateDay = today.date()
    dateTomorrow = dateDay - timedelta(days=16)
    dateYesterday = dateDay - timedelta(days=1)
    dateWeek = dateDay - timedelta(days=7)
    dateMonth = dateDay - timedelta(days=30)
    dateYear = dateDay - timedelta(days=365)
    
    # Queries
    simsAll = Sims.objects.all()
    ordersAll = Orders.objects.filter(order_date__range=(dateYear, dateDay))
    activationTomorrow = Orders.objects.filter(activation_date=dateTomorrow).count()
    
    orders_filter = []
    for order in ordersAll:
        try:
            type_sim = order.id_sim.type_sim
            operator = order.id_sim.operator
        except:
            type_sim = order.type_sim
            operator = '0'
        orders_filter.append({'date': order.order_date.date(), 'order': order.order_id, 'type': type_sim, 'oper': operator, 'month': order.order_date.strftime('%m (%b)'), 'year': order.order_date.date().year})
    
    # print('orders_filter',orders_filter)
    
    ordersWeek = [d for d in orders_filter if d["date"] >= dateWeek and d["date"] <= dateDay]    
    ordersMonth = [d for d in orders_filter if d["date"] >= dateMonth and d["date"] <= dateDay]
    ordersYear = [d for d in orders_filter if d["date"] >= dateYear and d["date"] <= dateDay]       
    
    # Converta a lista de dicionários em um DataFrame
    weekDf = pd.DataFrame(ordersWeek)
    monthDf = pd.DataFrame(ordersMonth)
    yearDf = pd.DataFrame(ordersYear)
    
    # WEEK
    # --- Sales
    weekSalesDup = weekDf.drop_duplicates(subset='order')
    weekSalesReport = weekSalesDup.groupby('date').size().reset_index(name='countSalesWeek')
    weekSalesDates = weekSalesReport['date'].tolist()
    weekSalesDays = [int((dateSalesWeek).strftime('%d')) for dateSalesWeek in weekSalesDates]
    weekSalesValues = weekSalesReport['countSalesWeek'].tolist()
    # --- SIMS
    weekSimsReport = weekDf.groupby(['date','type']).size().reset_index(name='countSimsWeek')
    weekSimsS = weekSimsReport[(weekSimsReport['type'] == 'esim')]
    weekSimsE = weekSimsReport[(weekSimsReport['type'] == 'sim')]
    weekSimsD = weekSimsS['date'].tolist()
    weekSimsDays = json.dumps([(dateSimsWeek).strftime('%d/%m') for dateSimsWeek in weekSimsD])   
    weekSimsValuesS = json.dumps(weekSimsS['countSimsWeek'].tolist())
    weekSimsValuesE = json.dumps(weekSimsE['countSimsWeek'].tolist())
    # --- Operator
    weekOperReport = weekDf.groupby(['date','oper']).size().reset_index(name='countOperWeek')
    weekOperTM = weekOperReport[(weekOperReport['oper'] == 'TM')]
    weekOperCM = weekOperReport[(weekOperReport['oper'] == 'CM')]
    weekOperTC = weekOperReport[(weekOperReport['oper'] == 'TC')]
    weekOperD = weekOperTM['date'].tolist()
    weekOperDates = json.dumps([(dateOperWeek).strftime('%d/%m') for dateOperWeek in weekOperD])   
    weekOperValuesTM = json.dumps(weekOperTM['countOperWeek'].tolist())
    weekOperValuesCM = json.dumps(weekOperCM['countOperWeek'].tolist())
    weekOperValuesTC = json.dumps(weekOperTC['countOperWeek'].tolist())
    
    # MONTH
    # --- Sales
    monthSalesDup = monthDf.drop_duplicates(subset='order')
    monthSalesReport = monthSalesDup.groupby('date').size().reset_index(name='countSalesMonth')
    monthSalesDates = monthSalesReport['date'].tolist()
    monthSalesDays = [int((dateSalesMonth).strftime('%d')) for dateSalesMonth in monthSalesDates]
    monthSalesValues = monthSalesReport['countSalesMonth'].tolist()
    # --- SIMS
    monthSimsReport = monthDf.groupby(['date','type']).size().reset_index(name='countSimsMonth')
    monthSimsS = monthSimsReport[(monthSimsReport['type'] == 'esim')]
    monthSimsE = monthSimsReport[(monthSimsReport['type'] == 'sim')]
    monthSimsD = monthSimsS['date'].tolist()
    monthSimsDays = json.dumps([(dateSimsMonth).strftime('%d') for dateSimsMonth in monthSimsD])
    monthSimsValuesS = json.dumps(monthSimsS['countSimsMonth'].tolist())
    monthSimsValuesE = json.dumps(monthSimsE['countSimsMonth'].tolist())
    # --- Operator
    monthOperReport = monthDf.groupby(['date','oper']).size().reset_index(name='countOperMonth')
    monthOperTM = monthOperReport[(monthOperReport['oper'] == 'TM')]
    monthOperCM = monthOperReport[(monthOperReport['oper'] == 'CM')]
    monthOperTC = monthOperReport[(monthOperReport['oper'] == 'TC')]
    monthOperD = monthOperTM['date'].tolist()
    monthOperDates = json.dumps([(dateOperMonth).strftime('%d') for dateOperMonth in monthOperD])
    monthOperValuesTM = json.dumps(monthOperTM['countOperMonth'].tolist())
    monthOperValuesCM = json.dumps(monthOperCM['countOperMonth'].tolist())
    monthOperValuesTC = json.dumps(monthOperTC['countOperMonth'].tolist())
    
    
    print('monthOperValuesTC')
    print(monthOperValuesTC)
    
    # YEAR
    # --- Sales
    yearSalesDup = yearDf.drop_duplicates(subset='order')        
    yearSalesReport = yearSalesDup.groupby('month').size().reset_index(name='countSalesYear')
    yearSalesDates = json.dumps(yearSalesReport['month'].tolist())
    yearSalesValues = json.dumps(yearSalesReport['countSalesYear'].tolist())
    # --- SIMS
    yearSimsReport = yearDf.groupby(['month','type']).size().reset_index(name='countSimsYear')
    yearSimsS = yearSimsReport[(yearSimsReport['type'] == 'esim')]
    yearSimsE = yearSimsReport[(yearSimsReport['type'] == 'sim')]
    yearSimsD = yearSimsS['month'].tolist()
    yearSimsDates = json.dumps(yearSimsD)
    yearSimsValuesS = json.dumps(yearSimsS['countSimsYear'].tolist())
    yearSimsValuesE = json.dumps(yearSimsE['countSimsYear'].tolist())
    # --- Operator
    yearOperReport = yearDf.groupby(['month','oper']).size().reset_index(name='countOperYear')
    yearOperTM = yearOperReport[(yearOperReport['oper'] == 'TM')]
    yearOperCM = yearOperReport[(yearOperReport['oper'] == 'CM')]
    yearOperTC = yearOperReport[(yearOperReport['oper'] == 'TC')]
    yearOperD = yearOperTM['month'].tolist()
    yearOperDates = json.dumps(yearOperD)
    yearOperValuesTM = json.dumps(yearOperTM['countOperYear'].tolist())
    yearOperValuesCM = json.dumps(yearOperCM['countOperYear'].tolist())
    yearOperValuesTC = json.dumps(yearOperTC['countOperYear'].tolist())
    
    print('yearOperValuesTC')
    print(yearOperValuesTC)

    # Verificar estoque de operadoras
    sim_tm = simsAll.filter(sim_status='DS',operator='TM', type_sim='sim').count()
    esim_tm = simsAll.filter(sim_status='DS',operator='TM', type_sim='esim').count()
    sim_cm = simsAll.filter(sim_status='DS',operator='CM', type_sim='sim').count()
    esim_cm = simsAll.filter(sim_status='DS',operator='CM', type_sim='esim').count()
    sim_tc = simsAll.filter(sim_status='DS',operator='TC', type_sim='sim').count()
    esim_tc = simsAll.filter(sim_status='DS',operator='TC', type_sim='esim').count()
    
    context= {
        'sims': simsAll,
        'sim_tm': sim_tm,
        'esim_tm': esim_tm,
        'sim_cm': sim_cm,
        'esim_cm': esim_cm,
        'sim_tc': sim_tc,
        'esim_tc': esim_tc,
        'dateDay': dateDay,
        'dateYesterday': dateYesterday,
        'dateWeek': dateWeek,
        'dateMonth': dateMonth,
        'dateYear': dateYear,
        'activationTomorrow': activationTomorrow,
        'weekSalesDates': weekSalesDays,
        'weekSalesValues': weekSalesValues,
        'weekSimsDates': weekSimsDays,
        'weekSimsValuesS': weekSimsValuesS,
        'weekSimsValuesE': weekSimsValuesE,        
        'weekOperDates': weekOperDates,
        'weekOperValuesTM': weekOperValuesTM,
        'weekOperValuesCM': weekOperValuesCM,
        'weekOperValuesTC': weekOperValuesTC,        
        'monthSalesDates': monthSalesDays,
        'monthSalesValues': monthSalesValues,
        'monthSimsDays': monthSimsDays,
        'monthSimsValuesS': monthSimsValuesS,
        'monthSimsValuesE': monthSimsValuesE,
        'monthOperDates': monthOperDates,
        'monthOperValuesTM': monthOperValuesTM,
        'monthOperValuesCM': monthOperValuesCM,
        'monthOperValuesTC': monthOperValuesTC,
        'yearSalesDates': yearSalesDates,
        'yearSalesValues': yearSalesValues,
        'yearSimsDates': yearSimsDates,
        'yearSimsValuesS': yearSimsValuesS,
        'yearSimsValuesE': yearSimsValuesE,
        'yearOperDates': yearOperDates,
        'yearOperValuesTM': yearOperValuesTM,
        'yearOperValuesCM': yearOperValuesCM,
        'yearOperValuesTC': yearOperValuesTC,
        
    }
    
    return render(request, 'painel/dashboard/index.html', context)
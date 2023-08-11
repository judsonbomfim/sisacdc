from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.sims.models import Sims

# Create your views here.
@login_required(login_url='/login/')
def index(request):
    
    sims = Sims.objects.all()
    
    # Verificar estoque de operadoras
    sim_tm = sims.filter(sim_status='DS',operator='TM', type_sim='sim').count()
    esim_tm = sims.filter(sim_status='DS',operator='TM', type_sim='esim').count()
    sim_cm = sims.filter(sim_status='DS',operator='CM', type_sim='sim').count()
    esim_cm = sims.filter(sim_status='DS',operator='CM', type_sim='esim').count()
    sim_tc = sims.filter(sim_status='DS',operator='TC', type_sim='sim').count()
    esim_tc = sims.filter(sim_status='DS',operator='TC', type_sim='esim').count()
    
       
    
    context= {
        'sims': sims,
        'sim_tm': sim_tm,
        'esim_tm': esim_tm,
        'sim_cm': sim_cm,
        'esim_cm': esim_cm,
        'sim_tc': sim_tc,
        'esim_tc': esim_tc,
    }
    
    return render(request, 'painel/dashboard/index.html', context)

from django.urls import path
from apps.sims.views import sims_list, sims_add_sim, sims_add_esim

urlpatterns = [
    path('listar/', sims_list, name='sims_index'),
    path('adicionar/sim/', sims_add_sim, name='sims_add_sim'),
    path('adicionar/esim/', sims_add_esim, name='sims_add_esim'),
]
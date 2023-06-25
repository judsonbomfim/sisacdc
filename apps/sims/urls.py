from django.urls import path
from apps.sims.views import sims_list, sims_add

urlpatterns = [
    path('lista/', sims_list, name='sims_index'),
    path('adicionar/', sims_add, name='sims_add'),
]
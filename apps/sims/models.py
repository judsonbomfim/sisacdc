from django.db import models

SIM_STATUS = [
    ('AT', 'Ativado'),
    ('CC', 'Cancelado'),    
    ('DS', 'Disponível'),
    ('DE', 'Desativado'),
    ('IN', 'Indisponível'),
    ('TC', 'Troca'),
]

SIM_OPERATOR = [
    ('TM', 'T-Mobile'), 
    ('CM', 'China Mobile'),
    ('TC', 'Telcom'),
    ('TI', 'Telcom IMSI'),
    ('MS', 'MoviStar'),
    ('OR', 'Orange'),
]

SIM_TYPES = [
    ('sim', 'SIM (Físico)'),   
    ('esim', 'eSIM (Virtual)'),
]

DATA = [
    ('20gb', '20GB'),
    ('50gb', '50GB')
]

class Sims(models.Model):
    id = models.AutoField(primary_key=True, serialize=False)
    sim = models.CharField(max_length=25)
    lpa = models.CharField(max_length=255, null=True, blank=True, )
    link = models.URLField(null=True, blank=True, default='-')
    type_sim =  models.CharField(max_length=20, choices=SIM_TYPES)
    data = models.CharField(max_length=15, null=True, blank=True, choices=DATA)
    operator = models.CharField(max_length=20, choices=SIM_OPERATOR)
    sim_status = models.CharField(max_length=20, choices=SIM_STATUS, default='DS')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'sims'
        verbose_name = 'Sim'
        verbose_name_plural = 'Sims'
        ordering = ['id']
    def __str__(self):
        return self.sim if self.sim else self.lpa
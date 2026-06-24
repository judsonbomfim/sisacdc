"""
Models do app **sims**.

Define o modelo :class:`Sims` que representa o inventário de cartões SIM
físicos e eSIMs, com suporte a múltiplas operadoras.
"""

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
    ('AT', 'AT&T'),
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
    """
    Representa um cartão SIM físico ou eSIM no inventário.

    Cada instância é um chip único identificado pelo ICCID (campo ``sim``)
    ou pelo LPA address (campo ``lpa``, para eSIMs).

    Atributos:
        sim (str): ICCID do SIM físico (número do chip).
        lpa (str): LPA address do eSIM (ex: ``LPA:1$sm-v4.com$ABC123``). Nulo para SIM físico.
        link (str): URL do QR code do eSIM após geração.
        type_sim (str): Tipo — ``sim`` (físico) ou ``esim`` (virtual).
        data (str): Franquia de dados do plano associado (``20gb`` ou ``50gb``).
        operator (str): Operadora — ``TC``, ``TI``, ``TM``, ``CM``, ``MS``, ``OR`` ou ``AT``.
        sim_status (str): Status atual no inventário (ver choices ``SIM_STATUS``).
        created_at (datetime): Data de cad as tro no sistema.
        updated_at (datetime): Data da última atualização.
    """
    id = models.AutoField(primary_key=True, serialize=False)
    sim = models.CharField(max_length=25)
    msisdn = models.IntegerField(null=True, blank=True)
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
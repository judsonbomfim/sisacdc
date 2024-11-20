from django.db import models
from apps.orders.models import Orders

NUNBER_STATUS = [
    ('AT', 'Ativado'),
    ('CC', 'Cancelado'),
    ('DS', 'Disponível'),
    ('IN', 'Indisponível'),
    ('TC', 'Troca'),  
]

VOICE_STATUS = [
    ('AA', 'Agd. Ativação'),
    ('AT', 'Ativado'),
    ('CC', 'Cancelado'),
    ('CN', 'Concluido'),
    ('DS', 'Desativado'),
    ('EE', 'Enviar E-mail'),
    ('PR', 'Processando'),
]

class VoiceNumbers(models.Model):
    id = models.AutoField(primary_key=True)
    login = models.CharField(max_length=15, null=True, blank=True)
    extension = models.IntegerField()
    number = models.IntegerField()
    password = models.CharField(max_length=15, null=True, blank=True)
    number_qrcode = models.CharField(max_length=45, null=True, blank=True)
    number_status = models.CharField(max_length=15, choices=NUNBER_STATUS, default='IN')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'voice_numbers'
        managed = True
        verbose_name = 'Número de Voz'
        verbose_name_plural = 'Número de Voz'
        ordering = ['id']
    def __str__(self):
        return self.number

class VoiceCalls(models.Model):
    id = models.AutoField(primary_key=True)
    id_item = models.ForeignKey(Orders, on_delete=models.DO_NOTHING, null=True, blank=True)
    id_number = models.ForeignKey(VoiceNumbers, on_delete=models.DO_NOTHING, null=True, blank=True)
    call_status = models.CharField(max_length=15, choices=VOICE_STATUS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'voice_calls'
        managed = True
        verbose_name = 'Chamada de Voz'
        verbose_name_plural = 'Chamadas de Voz'
        ordering = ['id_item']
    def __str__(self):
        return self.id_item
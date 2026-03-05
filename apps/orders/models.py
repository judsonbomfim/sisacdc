from django.db import models
from django.contrib.auth.models import User
from apps.sims.models import Sims

PRODUCT = [
    ('chamada-de-voz', 'Plano de Voz'),
    ('chip-internacional-eua', 'USA'),
    ('chip-internacional-eua-30-dias', 'USA 30 Dias'),
    ('chip-internacional-eua-e-canada', 'USA/CANADA'),
    ('chip-internacional-eua-canada-e-mexico', 'USA/CAN/MEX'),
    ('chip-internacional-america-do-norte-franquia-total', 'América do Norte F. Total'),
    ('chip-internacional-europa-plus', 'Europa Plus'),
    ('chip-internacional-europa', 'Europa'),
    ('chip-internacional-europa-ilimitado', 'Europa Ilimitado'),
    ('chip-internacional-europa-premium', 'Europa Premium'),
    ('chip-internacional-europa-1gb-total-05', 'Europa Total'),
    ('chip-internacional-europa-1gb-total', 'Europa Total'),
    ('chip-internacional-europa-franquia-total', 'Europa F. Total'),
    ('chip-internacional-global', 'Global'),
    ('chip-internacional-global-franquia-total', 'Global F. Total'),
    ('chip-internacional-america-do-sul', 'América do Sul'),
    ('chip-internacional-america-do-sul-premium', 'América do Sul Premium'),
    ('chip-internacional-america-do-sul-franquia-total', 'Am. do Sul F. Total'),
    ('chip-internacional-israel-premium', 'Israel Premium'),
    ('chip-internacional-tunisia-premium', 'Tunísia Premium'),
    ('chip-internacional-marrocos-premium', 'Marrocos Premium'),
    ('chip-internacional-egito-premium', 'Egito Premium'),
    ('chip-internacional-indonesia-premium', 'Indonésia Premium'),    
    ('chip-internacional-eua-premium', 'EUA Premium'),    
    ('chip-internacional-africa-premium', 'África Premium'),
    ('chip-internacional-africa-franquia-total', 'África F. Total'),
    ('chip-internacional-asia-premium', 'Ásia Premium'),
    ('chip-internacional-asia-franquia-total', 'Ásia F. Total'),
    ('chip-internacional-oriente-medio-premium', 'Oriente Médio Premium'),
    ('chip-internacional-oriente-medio-franquia-total', 'Oriente Médio F. Total'),
    ('chip-internacional-oceania-premium', 'Oceania Premium'),
    ('chip-internacional-oceania-franquia-total', 'Oceania F. Total'),
    ('chip-internacional-caribe-franquia-total', 'Caribe F. Total'),
]

DATA = [
    ('500mb-dia', '500MB'),
    ('1gb', '1GB'),
    ('2gb', '2GB'),
    ('ilimitado', 'Ilimitado'),
    ('20gb', '20GB'),
    ('50gb', '50GB'),
    ('world', 'World'),
]

ORDER_STATUS = [
    ('AA', 'Agd. Ativação'),
    ('AE', 'Agd. Envio'),
    ('AG', 'Agência'),
    ('AS', 'Atribuir SIM'),
    ('AI', 'Atribuir IMEI'),
    ('AT', 'Ativado'),
    ('CC', 'Cancelado'),
    ('CN', 'Concluido'),
    ('DE', 'Desativado'),
    ('DA', 'Data em Aberto'),
    ('EA', 'Erro Ativação'),
    ('ED', 'Erro Desativação'),
    ('EE', 'Enviar E-mail'),
    ('EI', 'Erro Importação'),
    ('ES', 'Em Separação'),
    ('MB', 'Motoboy'),
    ('PR', 'Processando'),
    ('PV', 'Plano de Voz'),
    ('RB', 'Reembolsado'),
    ('RE', 'Reembolsar'),
    ('RC', 'Reembolso Parcial'),
    ('RS', 'Reuso'),
    ('RP', 'Reprocessar'),
    ('RT', 'Retirada'),
    ('VS', 'Verificar SIM'),
]

CONDITION = [
    ('novo-sim', 'Novo SIM'),
    ('reuso-sim', 'Reutilizar')
]

class Orders(models.Model):
    id = models.AutoField(primary_key=True)
    order_id = models.IntegerField()
    item_id = models.CharField(max_length=64, unique=True, db_index=True)
    item_id_store = models.CharField(max_length=15, null=True, blank=True)
    client = models.CharField(max_length=70)
    email = models.CharField(max_length=70, null=True, blank=True)
    product = models.CharField(max_length=50, choices=PRODUCT)
    data_day = models.CharField(max_length=15, choices=DATA)
    qty = models.IntegerField()
    coupon = models.CharField(max_length=25, default=None)
    days = models.IntegerField()
    calls = models.BooleanField(default=False)
    countries = models.BooleanField(default=False)
    cell_mod = models.CharField(max_length=45, null=True, blank=True)
    cell_imei = models.CharField(max_length=35, null=True, blank=True)
    cell_eid = models.CharField(max_length=35, null=True, blank=True)
    ord_chip_nun = models.CharField(max_length=35, null=True, blank=True)
    shipping = models.CharField(max_length=40, null=True, blank=True)
    order_date = models.DateTimeField()
    activation_date = models.DateField()
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS, default='PR')
    type_sim = models.CharField(max_length=4, null=True, blank=True, default='sim')
    id_sim = models.ForeignKey(Sims, on_delete=models.DO_NOTHING, null=True, blank=True)
    condition = models.CharField(max_length=15, choices=CONDITION, default='novo-sim')
    tracking = models.CharField(max_length=25, null=True, blank=True)
    celular_samsung = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'orders'
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['order_id']
    def __str__(self):
        return f"Pedido #{self.id}"

TYPE_NOTE = [
    ('S', 'Sistema'),
    ('P', 'Privada'),
]

class Notes(models.Model):
    id = models.AutoField(primary_key=True)
    id_item = models.ForeignKey(Orders, on_delete=models.DO_NOTHING, related_name='order_notes', default=None)
    id_user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='user_notes', default=None, null=True, blank=True)
    note = models.TextField()
    type_note = models.CharField(max_length=1, choices=TYPE_NOTE, default='S')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'notes'
        verbose_name = 'Nota'
        verbose_name_plural = 'Notas'
        ordering = ['-id']
    def __str__(self):
        return f"Nota #{self.id}"
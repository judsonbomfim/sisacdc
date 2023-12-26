from django.db import models
from django.contrib.auth.models import User
from apps.sims.models import Sims

# make choice

PRODUCT = [
    ('chip-internacional-eua', 'USA'),
    ('chip-internacional-eua-e-canada', 'USA/CANADA'),
    ('chip-internacional-europa', 'EUROPA'),
    ('chip-internacional-global', 'GLOBAL')
]

DATA = [
    ('500mb-dia', '500MB'),
    ('1gb', '1GB'),
    ('2gb', '2GB'),
    ('ilimitado', 'Ilimitado')
]

ORDER_STATUS = [
    ('AA', 'Agd. Ativação'),
    ('AE', 'Agd. Envio'),
    ('AG', 'Agência'),
    ('AS', 'Atribuir SIM'),
    ('AT', 'Ativado'),
    ('CC', 'Cancelado'),
    ('CN', 'Concluido'),
    ('ES', 'Em Separação'),
    ('EE', 'Enviar eSIM'),
    ('MB', 'Motoboy'),
    ('PR', 'Processando'),
    ('RE', 'Reembolsar'),
    ('RB', 'Reembolsado'),
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
    item_id = models.CharField(max_length=15)
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'orders'
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['order_id']
    def __str__(self):
        return str(self.order_id)

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
        return str(self.id_item)
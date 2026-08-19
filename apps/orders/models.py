"""
Models do app **orders**.

Define os modelos principais de pedidos (:class:`Orders`) e notas (:class:`Notes`),
bem como as listas de escolhas (choices) usadas nesses modelos.
"""

from django.db import models
from django.contrib.auth.models import User
from apps.sims.models import Sims

PRODUCT = [
    ('chamada-de-voz', 'Plano de Voz'),
    ('chip-internacional-eua', 'USA'),
    ('chip-internacional-eua-30-dias', 'USA 30 Dias'),
    ('chip-internacional-eua-premium', 'EUA Premium'),    
    ('chip-internacional-america-do-norte', 'América do Norte'),
    ('chip-internacional-america-do-norte-franquia-total', 'América do Norte F. Total'),    
    ('chip-internacional-america-central', 'América Central'),
    ('chip-internacional-america-central-franquia-total', 'Am. Central F. Total'),    
    ('chip-internacional-europa', 'Europa'),
    ('chip-internacional-europa-franquia-total', 'Europa F. Total'),    
    ('chip-internacional-global', 'Global'),
    ('chip-internacional-global-franquia-total', 'Global F. Total'),    
    ('chip-internacional-america-do-sul', 'América do Sul'),
    ('chip-internacional-america-do-sul-franquia-total', 'Am. do Sul F. Total'),        
    ('chip-internacional-africa', 'África'),
    ('chip-internacional-africa-franquia-total', 'África F. Total'),    
    ('chip-internacional-asia', 'Ásia'),
    ('chip-internacional-asia-franquia-total', 'Ásia F. Total'),    
    ('chip-internacional-oriente-medio', 'Oriente Médio'),
    ('chip-internacional-oriente-medio-franquia-total', 'Oriente Médio F. Total'),    
    # Legado
    ('chip-internacional-eua-canada-e-mexico', 'USA/CAN/MEX'),
    ('chip-internacional-europa-premium', 'Europa Premium'),    
    ('chip-internacional-europa-1gb-total-05', 'Europa Total'),
    ('chip-internacional-europa-1gb-total', 'Europa Total'),
    ('chip-internacional-europa-ilimitado', 'Europa Ilimitado'),
    ('chip-fisico-internacional-europa-ilimitado', 'Europa F. Ilimitado'),    
    ('chip-internacional-africa-premium', 'África Premium'),
    ('chip-internacional-asia-premium', 'Ásia Premium'),
    ('chip-internacional-america-do-sul-premium', 'América do Sul Premium'),    
    ('chip-internacional-oriente-medio-premium', 'Oriente Médio Premium'),
    ('chip-internacional-oceania', 'Oceania'),
    ('chip-internacional-oceania-premium', 'Oceania Premium'),
    ('chip-internacional-oceania-franquia-total', 'Oceania F. Total'),    
    ('chip-internacional-caribe-franquia-total', 'Caribe F. Total'),

    # ('chip-internacional-europa-plus', 'Europa Plus'),
    # ('chip-internacional-eua-e-canada', 'USA/CANADA'),
    # ('chip-internacional-israel-premium', 'Israel Premium'),
    # ('chip-internacional-tunisia-premium', 'Tunísia Premium'),
    # ('chip-internacional-marrocos-premium', 'Marrocos Premium'),
    # ('chip-internacional-egito-premium', 'Egito Premium'),
    # ('chip-internacional-indonesia-premium', 'Indonésia Premium'),    

]

DATA = [
    ('500mb-dia', '500MB'),
    ('1gb', '1GB'),
    ('2gb', '2GB'),
    ('ilimitado', 'Ilimitado'),
    ('20gb', '20GB'),
    ('50gb', '50GB'),
    ('world', 'World'),
    ('10-ilimitado', 'Ilimitado (10)'),
    ('30-ilimitado', 'Ilimitado (30)'),
]

ORDER_STATUS = [
    ('AA', 'Agd. Ativação'),
    ('AE', 'Agd. Envio'),
    ('AO', 'Agd. Operadora'),
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
    ('SE', 'SIM sem Estoque'),
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
    """
    Representa um pedido importado do e-commerce (WooCommerce).

    Cada instância corresponde a um item de pedido (``item_id``) e rastreia
    todo o ciclo de vida — desde a importação (``PR``) até a conclusão (``CN``)
    ou cancelamento (``CC``).

    Atributos:
        order_id (int): ID do pedido no WooCommerce.
        item_id (str): ID único do item no pedido (índice principal).
        item_id_store (str): ID interno do item na loja (para atualizações via API).
        client (str): Nome completo do cliente.
        email (str): E-mail do cliente para notificações.
        product (str): Slug do produto (ver choices ``PRODUCT``).
        data_day (str): Franquia de dados do plano (ver choices ``DATA``).
        qty (int): Quantidade de itens no pedido.
        coupon (str): Código de cupom aplicado.
        days (int): Duração do plano em dias.
        calls (bool): Se o plano inclui chamadas de voz.
        countries (bool): Se o produto cobre múltiplos países.
        cell_mod (str): Modelo do celular do cliente (para compatibilidade eSIM).
        cell_imei (str): IMEI do celular (eSIM).
        cell_eid (str): EID do celular (eSIM).
        ord_chip_nun (str): Número de SIM para reuso (condição ``reuso-sim``).
        shipping (str): Método de envio selecionado.
        order_date (datetime): Data do pedido no e-commerce.
        activation_date (date): Data de ativação desejada pelo cliente.
        order_status (str): Status atual do pedido (ver choices ``ORDER_STATUS``).
        type_sim (str): Tipo de SIM — ``sim`` (físico) ou ``esim`` (virtual).
        id_sim (Sims): FK para o SIM atribuído ao pedido.
        order_sim (str): ICCID/SIM reservado manualmente.
        condition (str): Condição do SIM — ``novo-sim`` ou ``reuso-sim``.
        tracking (str): Código de rastreamento do envio físico.
        celular_samsung (bool): Indica se o celular é Samsung (impacta ativação eSIM).
    """
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
    order_sim = models.CharField(max_length=25, null=True, blank=True)
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
    """
    Notas internas associadas a um pedido.

    Usadas para registrar eventos do sistema (tipo ``S``) e observações
    privadas de operadores (tipo ``P``).

    Atributos:
        id_item (Orders): FK para o pedido ao qual a nota pertence.
        id_user (User): FK para o usuário que criou a nota (nulo se for do sistema).
        note (str): Conteúdo da nota.
        type_note (str): Tipo — ``S`` (Sistema) ou ``P`` (Privada).
        created_at (datetime): Data/hora de criação.
    """
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
# Generated by Django 4.2.2 on 2023-08-05 12:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0013_orders_cell_eid_orders_cell_imei_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orders',
            name='order_status',
            field=models.CharField(choices=[('AE', 'Agd. Envio'), ('AA', 'Agd. Ativação'), ('AS', 'Atribuir SIM'), ('AT', 'Ativado'), ('CC', 'Cancelado'), ('CN', 'Concluido'), ('MB', 'Motoboy'), ('PR', 'Processando'), ('RB', 'Reembolsado'), ('RS', 'Reuso'), ('RP', 'Reprocessar'), ('RT', 'Retirada'), ('VS', 'Verificar SIM')], default='PR', max_length=20),
        ),
    ]

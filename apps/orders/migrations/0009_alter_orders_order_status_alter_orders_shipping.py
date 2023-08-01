# Generated by Django 4.2.2 on 2023-07-31 12:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0008_alter_orders_order_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orders',
            name='order_status',
            field=models.CharField(choices=[('AE', 'Agd. Envio'), ('AS', 'Atribuir SIM'), ('AT', 'Ativado'), ('CC', 'Cancelado'), ('MB', 'Motoboy'), ('PR', 'Processando'), ('RB', 'Reembolsado'), ('RS', 'Reuso'), ('RP', 'Reprocessar'), ('RT', 'Retirada'), ('VS', 'Verificar SIM')], default='PR', max_length=20),
        ),
        migrations.AlterField(
            model_name='orders',
            name='shipping',
            field=models.CharField(max_length=40),
        ),
    ]

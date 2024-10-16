# Generated by Django 5.0 on 2024-03-22 15:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0032_alter_orders_order_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orders',
            name='order_status',
            field=models.CharField(choices=[('AA', 'Agd. Ativação'), ('AE', 'Agd. Envio'), ('AG', 'Agência'), ('AS', 'Atribuir SIM'), ('AI', 'Atribuir IMEI'), ('AT', 'Ativado'), ('CC', 'Cancelado'), ('CN', 'Concluido'), ('DS', 'Desativado'), ('ES', 'Em Separação'), ('EE', 'Enviar E-mail'), ('MB', 'Motoboy'), ('PR', 'Processando'), ('RE', 'Reembolsar'), ('RB', 'Reembolsado'), ('RS', 'Reuso'), ('RP', 'Reprocessar'), ('RT', 'Retirada'), ('VS', 'Verificar SIM')], default='PR', max_length=20),
        ),
    ]

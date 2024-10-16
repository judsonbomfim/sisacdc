# Generated by Django 5.0 on 2024-04-24 15:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0033_alter_orders_order_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orders',
            name='product',
            field=models.CharField(choices=[('chip-internacional-eua', 'USA'), ('chip-internacional-eua-e-canada', 'USA/CANADA'), ('chip-internacional-eua-canada-e-mexico', 'USA/CAN/MEX'), ('chip-internacional-europa', 'EUROPA'), ('chip-internacional-global', 'GLOBAL')], max_length=50),
        ),
    ]

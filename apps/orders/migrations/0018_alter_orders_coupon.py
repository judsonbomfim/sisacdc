# Generated by Django 4.2.2 on 2023-08-24 14:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0017_alter_orders_order_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orders',
            name='coupon',
            field=models.CharField(default=None, max_length=25),
        ),
    ]
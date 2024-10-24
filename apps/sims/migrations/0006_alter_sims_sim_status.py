# Generated by Django 5.0 on 2024-05-09 17:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sims', '0005_alter_sims_sim_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sims',
            name='sim_status',
            field=models.CharField(choices=[('AT', 'Ativado'), ('CC', 'Cancelado'), ('DS', 'Disponível'), ('DE', 'Desativado'), ('IN', 'Indisponível'), ('TC', 'Troca')], default='DS', max_length=20),
        ),
    ]

# Generated by Django 4.2.2 on 2023-06-07 21:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sims', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sims',
            name='link',
            field=models.URLField(blank=True, default='-', null=True),
        ),
    ]

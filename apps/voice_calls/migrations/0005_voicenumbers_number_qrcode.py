# Generated by Django 5.0 on 2024-03-07 18:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('voice_calls', '0004_rename_id_voice_voicecalls_id_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='voicenumbers',
            name='number_qrcode',
            field=models.CharField(blank=True, max_length=45, null=True),
        ),
    ]

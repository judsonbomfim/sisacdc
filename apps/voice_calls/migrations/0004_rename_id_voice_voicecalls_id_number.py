# Generated by Django 5.0 on 2024-03-06 14:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('voice_calls', '0003_rename_status_voicecalls_call_status'),
    ]

    operations = [
        migrations.RenameField(
            model_name='voicecalls',
            old_name='id_voice',
            new_name='id_number',
        ),
    ]
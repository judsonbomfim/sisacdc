# Generated by Django 5.0 on 2024-03-06 09:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('voice_calls', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='voicenumbers',
            old_name='status',
            new_name='number_status',
        ),
    ]
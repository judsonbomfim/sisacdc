from datetime import date

import pandas as pd
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.voice_calls.models import VoiceCalls
from apps.voice_calls.views import _python_date


class PythonDateTests(TestCase):
    def test_nat_e_none_viram_data_em_aberto(self):
        self.assertIsNone(_python_date(None))
        self.assertIsNone(_python_date(pd.NaT))

    def test_timestamp_vira_date(self):
        self.assertEqual(_python_date(pd.Timestamp('2026-10-08')), date(2026, 10, 8))


class VoiceListOpenDateTests(TestCase):
    def test_listagem_com_data_em_aberto_nao_retorna_500(self):
        user = User.objects.create_user(username='voz', password='voz-teste')
        VoiceCalls.objects.create(call_status='AA', days=7, activation_date=None)
        VoiceCalls.objects.create(call_status='AT', days=5, activation_date=date(2026, 10, 8))
        self.client.force_login(user)

        response = self.client.get(reverse('voice_index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '08/10/2026')
        self.assertContains(response, '12/10/2026')

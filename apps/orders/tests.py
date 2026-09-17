from datetime import date, datetime
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders.models import Notes, Orders
from apps.orders.tasks import normalize_type_sim
from apps.sims.models import Sims
from apps.voice_calls.models import VoiceCalls

WEBHOOK_SECRET = 'test-webhook-secret'


def _base_payload(**overrides):
    data = {
        'order_id': 1001,
        'order_number': '1001',
        'item_id': 2002,
        'product_id': 3003,
        'variation_id': 0,
        'iccid': '',
        'data_anterior': '2026-10-15',
        'data_nova': '2026-10-20',
        'user_id': 1,
        'origem': 'cliente',
        'alterado_em': '2026-09-11T20:31:00-03:00',
    }
    data.update(overrides)
    return data


def _create_order(**overrides):
    defaults = {
        'order_id': 1001,
        'item_id': '1001-1',
        'item_id_store': '2002',
        'client': 'Cliente Teste',
        'email': 'cliente@test.com',
        'product': 'chip-internacional-eua',
        'data_day': '1gb',
        'qty': 1,
        'coupon': '-',
        'days': 30,
        'calls': False,
        'activation_date': date(2026, 10, 15),
        'order_status': 'AS',
        'order_date': datetime(2026, 9, 1, 12, 0, 0),
    }
    defaults.update(overrides)
    return Orders.objects.create(**defaults)


@override_settings(WOO_WEBHOOK_SECRET=WEBHOOK_SECRET)
class DataAtivacaoWebhookTests(APITestCase):
    def setUp(self):
        self.url = reverse('orders_webhook_data_ativacao')
        self.headers = {'HTTP_X_WEBHOOK_SECRET': WEBHOOK_SECRET}
        notify_patcher = patch(
            'apps.orders.services.activation_date._notify_activation_date_changed'
        )
        self.notify_email = notify_patcher.start()
        self.addCleanup(notify_patcher.stop)

    def test_unauthorized_without_secret(self):
        response = self.client.post(self.url, _base_payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized_wrong_secret(self):
        response = self.client.post(
            self.url,
            _base_payload(),
            format='json',
            HTTP_X_WEBHOOK_SECRET='wrong',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_not_found(self):
        response = self.client.post(
            self.url,
            _base_payload(),
            format='json',
            **self.headers,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_updates_activation_date_and_note(self):
        order = _create_order()
        response = self.client.post(
            self.url,
            _base_payload(),
            format='json',
            **self.headers,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['updated'])

        order.refresh_from_db()
        self.assertEqual(order.activation_date, date(2026, 10, 20))
        self.assertTrue(
            Notes.objects.filter(
                id_item=order,
                note__contains='Data alterada de',
            ).exists()
        )
        self.notify_email.assert_called_once_with(order.pk)

    def test_idempotent_second_request(self):
        order = _create_order()
        payload = _base_payload()

        first = self.client.post(self.url, payload, format='json', **self.headers)
        second = self.client.post(self.url, payload, format='json', **self.headers)

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertTrue(first.data['updated'])
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertFalse(second.data['updated'])
        self.assertEqual(
            Notes.objects.filter(id_item=order, note__contains='Data alterada de').count(),
            1,
        )
        self.notify_email.assert_called_once_with(order.pk)

    def test_promotes_ei_to_as(self):
        order = _create_order(order_status='EI')
        response = self.client.post(
            self.url,
            _base_payload(),
            format='json',
            **self.headers,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.order_status, 'AS')

    def test_syncs_voice_calls(self):
        order = _create_order(calls=True)
        voice = VoiceCalls.objects.create(
            id_item=order,
            days=30,
            activation_date=date(2026, 10, 15),
            call_status='PR',
        )
        response = self.client.post(
            self.url,
            _base_payload(),
            format='json',
            **self.headers,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        voice.refresh_from_db()
        self.assertEqual(voice.activation_date, date(2026, 10, 20))

    def test_iccid_mismatch_returns_409(self):
        sim = Sims.objects.create(
            sim='8955TESTICCID0001',
            type_sim='sim',
            operator='TM',
            sim_status='AT',
        )
        order = _create_order(id_sim=sim)
        response = self.client.post(
            self.url,
            _base_payload(iccid='8955OTHER00000000'),
            format='json',
            **self.headers,
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_invalid_date_returns_400(self):
        _create_order()
        response = self.client.post(
            self.url,
            _base_payload(data_nova='31/10/2026'),
            format='json',
            **self.headers,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class NormalizeTypeSimTests(SimpleTestCase):
    def test_esim_variants(self):
        for raw in ('esim', 'eSIM', 'e-sim', 'E-SIM', 'chip-esim', ' e-sim '):
            self.assertEqual(normalize_type_sim(raw), 'esim', raw)

    def test_sim_variants_and_unknown(self):
        self.assertEqual(normalize_type_sim('sim'), 'sim')
        self.assertEqual(normalize_type_sim('sim-fisico'), 'sim')
        self.assertEqual(normalize_type_sim('físico'), 'sim')
        self.assertEqual(normalize_type_sim(None), 'sim')
        self.assertEqual(normalize_type_sim(''), 'sim')
        self.assertLessEqual(len(normalize_type_sim('sim-fisico')), 4)
        self.assertLessEqual(len(normalize_type_sim('e-sim')), 4)

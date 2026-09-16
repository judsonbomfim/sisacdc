import hmac

from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission


class AllowStoreWebhook(BasePermission):
    """Autentica webhooks server-to-server da loja via header X-Webhook-Secret."""

    message = 'Credenciais de webhook inválidas ou ausentes.'

    def has_permission(self, request, view):
        expected = settings.WOO_WEBHOOK_SECRET
        if not expected:
            raise AuthenticationFailed(self.message)
        provided = request.headers.get('X-Webhook-Secret', '')
        if not hmac.compare_digest(provided, expected):
            raise AuthenticationFailed(self.message)
        return True

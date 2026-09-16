import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.permissions import AllowStoreWebhook
from apps.orders.serializers import DataAtivacaoEventSerializer
from apps.orders.services.activation_date import (
    IccidMismatchError,
    OrderNotFoundError,
    apply_activation_date_from_store,
)

logger = logging.getLogger(__name__)


class DataAtivacaoEventView(APIView):
    """Recebe evento ``ae_data_ativacao_alterada`` enviado pelo plugin WordPress."""

    authentication_classes = []
    permission_classes = [AllowStoreWebhook]

    def post(self, request):
        serializer = DataAtivacaoEventSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        payload = serializer.validated_data
        try:
            result = apply_activation_date_from_store(payload)
        except OrderNotFoundError as exc:
            logger.warning('Webhook data-ativacao 404: %s', exc)
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except IccidMismatchError as exc:
            logger.warning('Webhook data-ativacao 409: %s', exc)
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(
            {
                'updated': result.updated,
                'order_pk': result.order_pk,
                'activation_date': result.activation_date,
            },
            status=status.HTTP_200_OK,
        )

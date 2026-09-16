from datetime import datetime

from rest_framework import serializers


class DataAtivacaoEventSerializer(serializers.Serializer):
    """Payload do evento WordPress ``ae_data_ativacao_alterada``."""

    order_id = serializers.IntegerField()
    order_number = serializers.CharField(required=False, allow_blank=True)
    item_id = serializers.IntegerField()
    product_id = serializers.IntegerField(required=False)
    variation_id = serializers.IntegerField(required=False, default=0)
    iccid = serializers.CharField(required=False, allow_blank=True, default='')
    data_anterior = serializers.CharField()
    data_nova = serializers.CharField()
    user_id = serializers.IntegerField(required=False)
    origem = serializers.CharField(required=False, allow_blank=True)
    alterado_em = serializers.CharField(required=False, allow_blank=True)

    def validate_data_nova(self, value):
        try:
            datetime.strptime(value, '%Y-%m-%d')
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError('Data inválida; use YYYY-MM-DD.') from exc
        return value

    def validate_data_anterior(self, value):
        if not value:
            return value
        try:
            datetime.strptime(value, '%Y-%m-%d')
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError('Data inválida; use YYYY-MM-DD.') from exc
        return value

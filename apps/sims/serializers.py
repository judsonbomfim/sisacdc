# seu_app/serializers.py
from rest_framework import serializers

class ConsumoSerializer(serializers.Serializer):
    iccid = serializers.CharField(max_length=100)
    mobile_data = serializers.FloatField()  # Ou IntegerField, dependendo do formato de mobile_data
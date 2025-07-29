from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..serializers import ConsumoSerializer
from ..classes import ApiTC
from rest_framework.permissions import IsAuthenticated

class ConsumoView(APIView):
    permission_classes = [IsAuthenticated]  # Requer autenticação JWT

    def get(self, request, iccid):
        try:
            # Chama o método mobileData da classe ApiTC
            mobile_data = ApiTC.mobileData(iccid)
            # Serializa os dados
            serializer = ConsumoSerializer(data={
                "iccid": iccid,
                "mobile_data": mobile_data
            })
            if serializer.is_valid():
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Tratamento genérico de erros
            return Response({"error": f"Erro ao consultar consumo: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..serializers import ConsumoSerializer
from ..classes import ApiTC, ApiCM
from rest_framework.permissions import IsAuthenticated
from apps.sims.models import Sims

class ConsumoView(APIView):
    permission_classes = [IsAuthenticated]  # Requer autenticação JWT

    def get(self, request, iccid):
        sim = Sims.objects.filter(sim=iccid).first()
        sim_operator = sim.operator if sim else None
        print(f"ICCID recebido: {iccid}")
        print(f"Operadora do SIM: {sim_operator}")

        try:
            if sim_operator == 'TC':
                mobile_data = ApiTC.mobileData(iccid)
            elif sim_operator == 'CM':
                mobile_data = ApiCM.mobileData(iccid)
            serializer = ConsumoSerializer(data={
                "iccid": iccid,
                "mobile_data": mobile_data
            })
            if serializer.is_valid():
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Erro ao consultar consumo: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
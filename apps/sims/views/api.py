from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..serializers import ConsumoSerializer
from ..classes import ApiTC, ApiCM, ApiCMHK
from rest_framework.permissions import IsAuthenticated
from apps.sims.models import Sims
from apps.orders.models import Orders
import logging
logger = logging.getLogger(__name__)


def _consumo_data_day_for_sim(sim):
    if not sim:
        return None
    order = (
        Orders.objects.filter(id_sim=sim)
        .exclude(order_status__in=('CC', 'RB', 'CN'))
        .order_by('-activation_date', '-id')
        .first()
    )
    return order.data_day if order else None


class ConsumoView(APIView):
    permission_classes = [IsAuthenticated]  # Requer autenticação JWT

    def get(self, request, iccid):
        sim = Sims.objects.filter(sim=iccid).first()
        sim_operator = sim.operator if sim else None

        try:
            if sim_operator == 'TC' or sim_operator == 'TI':
                mobile_data = ApiTC.mobileData(iccid)
            elif sim_operator == 'CM':
                mobile_data = ApiCM.mobileData(iccid, _consumo_data_day_for_sim(sim))
            elif sim_operator == 'CMHK':
                mobile_data = ApiCMHK.mobileData(iccid, _consumo_data_day_for_sim(sim))
            serializer = ConsumoSerializer(data={
                "iccid": iccid,
                "mobile_data": mobile_data
            })
            if serializer.is_valid():
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Erro ao consultar consumo: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
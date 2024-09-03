from rest_framework import exceptions, generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt import authentication
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .serializers import ProvidingSerializers, ProviderHistorySerializers
from app_Utils.permissions import IsLevel1, IsTwoFAEnabled, IsTwoFAValidated, CheckTokenExclusivity
from app_Swap_Pool.models import Pool
from app_Swap_Providing.models import Provider, ProviderHistory


class ProvidingView(generics.CreateAPIView):
    serializer_class = ProvidingSerializers
    permission_classes = [IsAuthenticated, IsLevel1, IsTwoFAEnabled, IsTwoFAValidated, CheckTokenExclusivity]

    def get(self, request):
        ser = self.get_serializer(data=self.request.query_params)
        if ser.is_valid():
            return Response({
                "status": True,
                "result": ser.validated_data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": False,
                "message": ser.errors[list(ser.errors)[0]][0]
            }, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        ser = self.get_serializer(data=self.request.data)
        if ser.is_valid():
            ser = ser.save()
            return Response({
                "status": True,
                'message': 'تراکنش شما با موفقیت انجام شد',
                "result": ser
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "status": False,
                "message": ser.errors[list(ser.errors)[0]][0]
            }, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        user = None
        if request and hasattr(request, "user"):
            user = authentication.JWTAuthentication().authenticate(request)[0]
        if user is None:
            return Response({
                "status": False,
                "message": "کاربری یافت نشد"
            }, status=status.HTTP_400_BAD_REQUEST)
        if self.request.data.get('currency_A_symbol') and self.request.data.get('currency_B_symbol'):
            returned_list = Pool.objects.find_by_currencies_symbol(self.request.data.get('currency_A_symbol'), self.request.data.get('currency_B_symbol'))
            pool = returned_list[0]
            if not pool:
                raise exceptions.ParseError({
                    "status": False,
                    "message": "استخر وجود ندارد"
                })
            provider = Provider.objects.find_by_user_pool(user, pool)
            if not provider:
                raise exceptions.ParseError({
                    "status": False,
                    "message": "کاربر در این استخر وجود ندارد"
                })
            ser = self.get_serializer(instance=provider, data=self.request.data)
            if ser.is_valid():
                ser = ser.save()
                return Response({
                    "status": True,
                    'message': 'تراکنش شما با موفقیت انجام شد',
                    "result": ser
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    "status": False,
                    "message": ser.errors[list(ser.errors)[0]][0]
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                "status": False,
                "message": "ارسال نماد ارز ها الزامی است"
            }, status=status.HTTP_400_BAD_REQUEST)

class ProviderHistoryView(generics.ListAPIView, PageNumberPagination):
    serializer_class = ProviderHistorySerializers
    permission_classes = [IsAuthenticated, IsLevel1, IsTwoFAEnabled, IsTwoFAValidated, CheckTokenExclusivity]
    page_size_query_param = 'limit'

    def get(self, request):
        try:
            pool_id = int(self.request.query_params['pool_id'])
        except:
            pool_id = None
        provider_transactions = ProviderHistory.objects.find_by_last(pool_id=pool_id)
        provider_transactions = self.paginate_queryset(provider_transactions)
        ser = self.get_serializer(provider_transactions, many=True)
        return self.get_paginated_response(ser.data)

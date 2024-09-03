from rest_framework import exceptions, generics, status
from rest_framework_simplejwt import authentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from app_Swap_Pool.models import Pool

from .serializers import PoolsDetailSerializers, PoolsCurrenciesSerializers, HomeSerializers
from app_Utils.permissions import IsLevel1, IsTwoFAEnabled, IsTwoFAValidated, CheckTokenExclusivity
from app_Swap_Providing.models import Provider


class PoolsDetailView(generics.CreateAPIView):
    serializer_class = PoolsDetailSerializers
    permission_classes = [IsAuthenticated, IsLevel1, IsTwoFAEnabled, IsTwoFAValidated, CheckTokenExclusivity]

    def get(self, request):
        ser = self.get_serializer(data=self.request.query_params)
        if ser.is_valid():
            return Response({
                'status': True,
                'result': ser.validated_data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": False,
                "message": ser.errors[list(ser.errors)[0]][0]
            }, status=status.HTTP_400_BAD_REQUEST)


class UserActivePoolsView(generics.ListAPIView, PageNumberPagination):
    serializer_class = PoolsDetailSerializers
    permission_classes = [IsAuthenticated, IsLevel1, IsTwoFAEnabled, IsTwoFAValidated, CheckTokenExclusivity]
    page_size_query_param = 'limit'

    def get(self, request):
        user = None
        if request and hasattr(request, "user"):
            user = authentication.JWTAuthentication().authenticate(request)[0]
        if user is None:
            raise exceptions.ParseError({
                "status": False,
                "message": "کاربر یافت نشد"
            })

        result = Provider.objects.find_pool_by_user(user=user, only_has_liquidity=False)
        user_pools = result['user_pools']
        user_providing = result['user_providing']
        user_pools = self.paginate_queryset(user_pools)
        user_pools_ser = self.get_serializer(user_pools, many=True).data
        for index, providing in enumerate(user_providing):
            user_pools_ser[index]['irt_value'] = providing.pool.cal_total_value_locked(base_currency='IRT')
            user_pools_ser[index]['user_share'] = providing.get_share()
            user_pools_ser[index]['user_amount_A'] = providing.get_amount_A()
            user_pools_ser[index]['user_amount_B'] = providing.get_amount_B()

        return self.get_paginated_response(user_pools_ser)


class CurrenciesView(generics.ListAPIView):
    serializer_class = PoolsCurrenciesSerializers
    permission_classes = [IsAuthenticated, IsLevel1, IsTwoFAEnabled, IsTwoFAValidated, CheckTokenExclusivity]

    def get(self, request):
        user = None
        if request and hasattr(request, "user"):
            user = authentication.JWTAuthentication().authenticate(request)[0]
        if user is None:
            raise exceptions.ParseError({
                "status": False,
                "message": "کاربر یافت نشد"
            })

        try:
            currency_symbol = self.request.query_params['currency_symbol'].upper()
        except:
            currency_symbol = None

        if currency_symbol is not None and not Pool.objects.filter_by_currency(currency_symbol):
            raise exceptions.ParseError({
                "status": False,
                "message": "برای این توکن استخری وجود ندارد"
            })
        currencies_symbol = Pool.objects.find_currencies_symbol() if currency_symbol is None else [currency_symbol]
        request_data = []
        for currency_symbol in currencies_symbol:
            request_data.append({'currency_symbol': currency_symbol})
        ser = self.get_serializer(request_data, many=True)
        return Response({
            'status': True,
            'result': ser.data
        }, status=status.HTTP_200_OK)


class HomeView(generics.ListAPIView):
    serializer_class = HomeSerializers
    permission_classes = [IsAuthenticated, IsLevel1, IsTwoFAEnabled, IsTwoFAValidated, CheckTokenExclusivity]

    def get(self, request):
        user = None
        if request and hasattr(request, "user"):
            user = authentication.JWTAuthentication().authenticate(request)[0]
        if user is None:
            raise exceptions.ParseError({
                "status": False,
                "message": "کاربر یافت نشد"
            })

        ser = self.get_serializer({}, many=False)
        return Response({
            'status': True,
            'result': ser.data
        }, status=status.HTTP_200_OK)

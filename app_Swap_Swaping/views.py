from rest_framework import generics, status, exceptions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt import authentication

from app_Swap_Pool.models import Pool


from .serializers import SwapingSerializers
from app_Swap_Swaping.models import SwapHistory
from app_Utils.permissions import IsLevel1, IsTwoFAEnabled, IsTwoFAValidated, CheckTokenExclusivity


class SwapingView(generics.CreateAPIView):
    serializer_class = SwapingSerializers
    permission_classes = [IsAuthenticated, IsLevel1, IsTwoFAEnabled, IsTwoFAValidated, CheckTokenExclusivity]

    def post(self, request, *args, **kwargs):
        ser = self.get_serializer(data=self.request.data)
        if ser.is_valid():
            ser = ser.save()
            return Response({
                "status": True,
                'message': 'سواپ شما با موفقیت انجام شد',
                "result": ser
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "status": False,
                "message": ser.errors[list(ser.errors)[0]][0]
            }, status=status.HTTP_400_BAD_REQUEST)

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


class SwapHistoryView(generics.ListAPIView, PageNumberPagination):
    serializer_class = SwapingSerializers
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
        try:
            pool = Pool.objects.find_by_id(id=int(self.request.query_params['pool_id']))
            pool = None if not pool else pool
        except:
            pool = None
        try:
            this_user = user if self.request.query_params['this_user'] == 'True' else None
        except:
            this_user = None
        
        swap_transactions = SwapHistory.objects.find_by_user_pool_last(user=this_user, pool=pool)
        swap_transactions = self.paginate_queryset(swap_transactions)
        ser = self.get_serializer(swap_transactions, many=True)
        return self.get_paginated_response(ser.data)

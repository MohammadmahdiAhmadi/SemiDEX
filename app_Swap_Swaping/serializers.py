from rest_framework import serializers, exceptions
from rest_framework_simplejwt import authentication
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MinValueValidator
import pytz

from khayyam import JalaliDatetime
from app_Utils.functions import TehranTimezone
from datetime import datetime
from app_Swap_Pool.models import Pool
from app_Swap_Pool.serializers import CurrencySerializer
from app_Swap_Swaping.models import SwapHistory
from app_Wallet.models import Wallet


class SwapingSerializers(serializers.ModelSerializer):
    """
    serilizer for swaping and pre swaping
    """
    default_error_messages = {
        'user_does_not_exists': {
            "status": False,
            "message": _("کاربر یافت نشد")
        },
        'pool_does_not_exists': {
            "status": False,
            "message": _("استخر یافت نشد")
        },
        'user_already_in_this_pool': {
            "status": False,
            "message": _("کاربر هم اکنون در این استخر میباشد")
        },
        'A_value_is_not_equal_to_B_value': {
            "status": False,
            "message": _("ارزش دلاری ارز اول با ارزش دلاری ارز دوم برابر نیست")
        },
        'remove_percent_cant_be_zero': {
            "status": False,
            "message": _("درصد برداشت از استخر نمیتواند صفر باشد")
        },
        'pool_is_suspended_for_now': {
            "status": False,
            "message": _("تا اطلاع ثانوی سواپ در این استخر غیرفعال می باشد")
        },
        'currency_A_symbol_is_required': {
            "status": False,
            "message": _("ارسال نماد ارز اول الزامی است")
        },
        'currency_B_symbol_is_required': {
            "status": False,
            "message": _("ارسال نماد ارز دوم الزامی است")
        },
        'pool_is_empty': {
            "status": False,
            "message": _("امکان سواپ در این استخر به دلیل نبود نقدینگی وجود ندارد")
        },
    }
    time = serializers.SerializerMethodField('get_time', read_only=True)

    input_currency_symbol = serializers.CharField(required=True, write_only=True, error_messages={
        'required': 'ارسال نماد ارز آورده الزامی است',
        'blank': 'فیلد نماد ارز آورده نباید خالی باشد'
    })
    output_currency_symbol = serializers.CharField(required=True, write_only=True, error_messages={
        'required': 'ارسال نماد ارز دریافتی الزامی است',
        'blank': 'فیلد نماد ارز دریافتی نباید خالی باشد'
    })
    input_amount = serializers.FloatField(required=True, write_only=False, error_messages={
        'required': 'ارسال مقدار ارز آورده الزامی است',
        'blank': 'فیلد مقدار ارز آورده نباید خالی باشد'
    }, validators=[MinValueValidator(0.0)])
    max_slippage_tolerance = serializers.FloatField(write_only=True, required=True, error_messages={
        'required': 'ارسال درصد تلرانس الزامی است',
        'blank': 'فیلد درصد تلرانس نباید خالی باشد'
    }, validators=[MinValueValidator(0.0)])

    input_currency = CurrencySerializer(many=False, read_only=True)
    output_currency = CurrencySerializer(many=False, read_only=True)

    class Meta:
        model = SwapHistory
        fields = (
            'input_currency',
            'output_currency',
            'output_amount',
            'fee_amount',
            'fee_percentage',
            'before_price',
            'after_price',
            'slippage_tolerance',
            'equivalent_irt',
            'equivalent_usdt',
            'equivalent_btc',
            'time',

            'input_amount',
            'input_currency_symbol',
            'output_currency_symbol',
            'max_slippage_tolerance'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')

        self.fields['max_slippage_tolerance'].required = False if request.method == "GET" else True

    def get_time(self, obj): 
        """
        time in jalali and calculating diffrence_time between now and swap
        """
        user_history_jalali_time = JalaliDatetime(datetime.strptime(str(obj.time), '%Y-%m-%d %H:%M:%S.%f%z').astimezone(tz=TehranTimezone())).isoformat().split("T")
        user_history_time = user_history_jalali_time[1].split(".")[0].split(":")
        diffrence_time = datetime.now(tz=pytz.utc) - obj.time
        return [user_history_jalali_time[0], f"{user_history_time[0]}:{user_history_time[1]}", divmod(diffrence_time.total_seconds(), 60)[0]]
    
    def validate(self, attrs):
        self.user = None
        request = self.context["request"]
        if request and hasattr(request, "user"):
            self.user = authentication.JWTAuthentication().authenticate(request)[0]
        if self.user is None:
            raise exceptions.ParseError(
                self.error_messages['user_does_not_exists'], 'user_does_not_exists'
            )

        returned_list = Pool.objects.find_by_currencies_symbol(attrs['input_currency_symbol'], attrs['output_currency_symbol'], is_reverse=True) # find all pools with this input_currency_symbol and output_currency_symbol
        self.pool = returned_list[0]
        self.is_reverse = returned_list[1]
        if self.pool is None:
            raise exceptions.ParseError(
                self.error_messages['pool_does_not_exists'], 'pool_does_not_exists'
            )

        if request.method == 'GET':
            pre_swaping = self.pool.swaping(input_amount=attrs['input_amount'], is_reverse=self.is_reverse, update_pool=False) # pre swaping
            input_wallet = Wallet.objects.find_by_currency_symbol_and_merge_to_last(self.user, attrs['input_currency_symbol'])
            return {
                'balance': input_wallet.available, # current balance
                'balance_in_irt': input_wallet.available * Pool.objects.cal_price(input_wallet.excurrency.currency.symbol, base_currency_symbol='IRT'), # currenct balance in IRT
                'before_price': self.pool.cal_price(is_reverse=self.is_reverse), # price before this swap
                'after_price': pre_swaping['final_price'], # price after this swap
                'output_amount': pre_swaping['output_amount'], # received amount of output currency
                'fee_amount': pre_swaping['fee_amount'], # amount of fee that user should pay in this swap
                'slippage_tolerance': pre_swaping['slippage_tolerance'], # slippage_tolerance of this swap
            }

        return attrs

    def create(self, validated_data):
        if self.pool.suspend_swap is True:
            raise exceptions.ParseError(
                self.error_messages['pool_is_suspended_for_now'], 'pool_is_suspended_for_now'
            )
        pool_price = self.pool.cal_price(is_reverse=self.is_reverse)
        if (pool_price == -1) or (self.pool.amount_A==0 and self.pool.amount_B==0): # check pool liquidity
            raise exceptions.ParseError(
                self.error_messages['pool_is_empty'], 'pool_is_empty'
            )

        pre_swaping = self.pool.swaping(input_amount=validated_data['input_amount'], is_reverse=self.is_reverse, update_pool=False) # pre swaping for calcculating slippage_tolerance
        if pre_swaping['slippage_tolerance'] > validated_data['max_slippage_tolerance']: # check slippage_tolerance
            raise exceptions.ParseError({
                "status": False,
                "message": _(f"سواپ شما به دلیل اختلاف تلرانس بیش از حد مجاز مشخص شده، انجام نشد"),
                "result": {
                    "max_slippage_tolerance": validated_data['max_slippage_tolerance'],
                    "slippage_tolerance": pre_swaping['slippage_tolerance']
                }
            })

        input_wallet = Wallet.objects.find_by_currency_symbol_and_merge_to_last(self.user, validated_data['input_currency_symbol'])
        output_wallet = Wallet.objects.find_by_currency_symbol_and_merge_to_last(self.user, validated_data['output_currency_symbol'])
        if not input_wallet.check_available_balance(validated_data['input_amount']): # check user balance
            raise exceptions.ParseError({
                "status": False,
                "message": _(f"موجودی {input_wallet.excurrency.currency.name_fa} شما کافی نمیباشد")
            })

        input_wallet.low_balance(validated_data['input_amount']) # low user input_wallet balance
        swaping = self.pool.swaping(input_amount=validated_data['input_amount'], is_reverse=self.is_reverse, update_pool=True) # doing swap
        output_wallet.add_balance(swaping['output_amount'], add_net=False) # add output_amount in output_wallet

        swap = SwapHistory.objects.create_new_swap(
            user=self.user,
            pool=self.pool,
            input_currency=input_wallet.excurrency.currency,
            output_currency=output_wallet.excurrency.currency,
            input_amount=validated_data['input_amount'],
            output_amount=swaping['output_amount'],
            fee_amount=swaping['fee_amount'],
            before_price=pool_price,
            after_price=swaping['final_price'],
            slippage_tolerance=swaping['slippage_tolerance']
        )

        swap_ser = SwapingSerializers(swap, many=False, context={"request": self.context.get('request')}).data

        return swap_ser

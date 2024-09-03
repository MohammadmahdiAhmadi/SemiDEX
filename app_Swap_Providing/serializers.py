from rest_framework import serializers, exceptions
from rest_framework_simplejwt import authentication
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MaxValueValidator, MinValueValidator
from khayyam import JalaliDatetime
from datetime import datetime
import math

from app_Swap_Pool.models import Pool
from app_Swap_Providing.models import Provider, ProviderHistory
from app_Wallet.models import Wallet
from app_Utils.classes import CurrenciesPrice
from app_Utils.functions import TehranTimezone


class ProviderSerializers(serializers.ModelSerializer):
    """
    show information of a provider
    """
    is_active_for_user = serializers.SerializerMethodField('get_is_active_for_user', read_only=True)
    tvl_irt = serializers.SerializerMethodField('get_tvl_irt', read_only=True)
    present_share = serializers.SerializerMethodField('get_present_share', read_only=True)
    present_amount_A = serializers.SerializerMethodField('get_present_amount_A', read_only=True)
    present_amount_B = serializers.SerializerMethodField('get_present_amount_B', read_only=True)
    primary_share = serializers.SerializerMethodField('get_primary_share', read_only=True)
    primary_amount_A = serializers.SerializerMethodField('get_primary_amount_A', read_only=True)
    primary_amount_B = serializers.SerializerMethodField('get_primary_amount_B', read_only=True)

    class Meta:
        model = Provider
        fields = (
            'is_active_for_user',
            'tvl_irt',
            'present_share',
            'present_amount_A',
            'present_amount_B',
            'primary_share',
            'primary_amount_A',
            'primary_amount_B',
        )

    def get_is_active_for_user(self, obj):
        """
        :return: is it active for this user or not?
        """
        return None if not obj else True if obj.lp_tokens > 0 else False

    def get_tvl_irt(self, obj):
        """
        :return: get total value locked of this provider based on IRT
        """
        return obj.pool.cal_total_value_locked(base_currency='IRT', amount_A=obj.get_amount_A(), amount_B=obj.get_amount_B())

    def get_present_share(self, obj):
        """
        :return: get present share of this provider
        """
        return obj.get_share()

    def get_present_amount_A(self, obj):
        """
        :return: get present amount_A of this provider
        """
        return obj.get_amount_A()

    def get_present_amount_B(self, obj):
        """
        :return: get present amount_B of this provider
        """
        return obj.get_amount_B()

    def get_primary_share(self, obj):
        """
        :return: get primary share of this provider (when activating)
        """
        first_transaction = ProviderHistory.objects.find_by_provider(provider=obj)
        return first_transaction.lp_tokens_difference / first_transaction.lp_tokens_pool if first_transaction else -1

    def get_primary_amount_A(self, obj):
        """
        :return: get primary amount_A of this provider (when activating)
        """
        first_transaction = ProviderHistory.objects.find_by_provider(provider=obj)
        return first_transaction.amount_A if first_transaction else -1

    def get_primary_amount_B(self, obj):
        """
        :return: get primary amount_B of this provider (when activating)
        """
        first_transaction = ProviderHistory.objects.find_by_provider(provider=obj)
        return first_transaction.amount_B if first_transaction else -1


class ProvidingSerializers(serializers.ModelSerializer):
    """
    be provider in a pool or increase/decrease liquidity of a pool
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
        'pool_is_empty': {
            "status": False,
            "message": _("استخر خالی است")
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
            "message": _("تا اطلاع ثانوی تراکنش در این استخر غیرفعال می باشد")
        },
        'currency_A_symbol_is_required': {
            "status": False,
            "message": _("ارسال نماد ارز اول الزامی است")
        },
        'currency_B_symbol_is_required': {
            "status": False,
            "message": _("ارسال نماد ارز دوم الزامی است")
        },
        'you_dont_have_liquidity': {
            "status": False,
            "message": _("شما در این استخر نقدینگی ندارید")
        },
    }

    currency_A_symbol = serializers.CharField(required=True, write_only=True, error_messages={
        'required': 'ارسال نماد ارز اول الزامی است',
        'blank': 'فیلد نماد ارز اول نباید خالی باشد'
    })
    currency_B_symbol = serializers.CharField(required=True, write_only=True, error_messages={
        'required': 'ارسال نماد ارز دوم الزامی است',
        'blank': 'فیلد نماد ارز دوم نباید خالی باشد'
    })
    amount_A = serializers.FloatField(write_only=True, error_messages={
        'required': 'ارسال مقدار ارز اول الزامی است',
        'blank': 'فیلد مقدار ارز اول نباید خالی باشد'
    }, validators=[MinValueValidator(0.0)])
    amount_B = serializers.FloatField(write_only=True, error_messages={
        'required': 'ارسال مقدار ارز دوم الزامی است',
        'blank': 'فیلد مقدار ارز دوم نباید خالی باشد'
    }, validators=[MinValueValidator(0.0)])
    type = serializers.ChoiceField(choices=['add', 'remove'], write_only=True, error_messages={
        "invalid_choice": _("نوع تراکنش انتخابی اشتباه است"),
        'required': "ارسال نوع تراکنش (افزودن یا کاهش) برای تغییر مقادیر تامین کنندگی اجباری است",
        'blank': "نوع تراکنش (افزودن یا کاهش) برای تغییر مقادیر تامین کنندگی نباید خالی باشد"
    })
    remove_percent = serializers.FloatField(write_only=True, error_messages={
        'required': 'ارسال درصد برداشت از استخر الزامی است',
        'blank': 'فیلد درصد برداشت از استخر نباید خالی باشد'
    }, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],)


    class Meta:
        model = Provider
        fields = (
            'currency_A_symbol',
            'currency_B_symbol',
            'amount_A',
            'amount_B',
            'type',
            'remove_percent'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        data = request.query_params if request.method == "GET" else request.data

        self.fields['amount_A'].required = False if (request.method == "GET" and data.get('type') == 'remove') or request.method == "PUT" else True
        self.fields['amount_B'].required = False if (request.method == "GET" or request.method == "PUT") else True
        self.fields['remove_percent'].required = True if (request.method == "GET" and data.get('type') == 'remove') or request.method == "PUT" else False
        self.fields['type'].required = True if request.method == "GET" else False

    def validate(self, attrs):
        self.user = None
        request = self.context["request"]
        if request and hasattr(request, "user"):
            self.user = authentication.JWTAuthentication().authenticate(request)[0]
        if self.user is None:
            raise exceptions.ParseError(
                self.error_messages['user_does_not_exists'], 'user_does_not_exists'
            )

        returned_list = Pool.objects.find_by_currencies_symbol(attrs['currency_A_symbol'], attrs['currency_B_symbol'], is_reverse=True)
        self.pool = returned_list[0]
        self.is_reverse = returned_list[1] # when user enter currency_A symbol instead of currency_B symbol and vice versa
        if self.pool is None:
            raise exceptions.ParseError(
                self.error_messages['pool_does_not_exists'], 'pool_does_not_exists'
            )

        if request.method == 'GET': # pre providing
            if attrs['type'] == 'add': # user want increase liquidity
                wallet_A = Wallet.objects.find_by_currency_symbol_and_merge_to_last(self.user, attrs['currency_A_symbol']) # user wallet of currency_A
                wallet_B = Wallet.objects.find_by_currency_symbol_and_merge_to_last(self.user, attrs['currency_B_symbol']) # user wallet of currency_B
                pool_price = self.pool.cal_price() if not self.is_reverse else (1 / self.pool.cal_price()) # get pool price
                if pool_price == -1: # pool is empty and we can't get price of that, so we get price from global markets
                    pool_price = 0
                    currencies_price_class = CurrenciesPrice()
                    currency_A_price_USDT = currencies_price_class.cal_value_in_usdt(attrs['currency_A_symbol'], 1)
                    currency_B_price_USDT = currencies_price_class.cal_value_in_usdt(attrs['currency_B_symbol'], 1)
                    necessary_amount_B = (attrs['amount_A'] * currency_A_price_USDT) / currency_B_price_USDT
                else:
                    necessary_amount_B = pool_price * attrs['amount_A']
                received_lp_tokens = math.sqrt(attrs['amount_A'] * necessary_amount_B)
                provider = Provider.objects.find_by_user_pool(self.user, self.pool)
                return {
                    'type': attrs['type'],
                    'amount_A': attrs['amount_A'],
                    'amount_B': necessary_amount_B,
                    'new_amount_A': attrs['amount_A'] + provider.get_amount_A() if provider else attrs['amount_A'], # new amount_A of this provider
                    'new_amount_B': necessary_amount_B + provider.get_amount_B() if provider else necessary_amount_B, # new amount_B of this provider
                    'new_share': (provider.lp_tokens + received_lp_tokens) / (self.pool.lp_tokens + received_lp_tokens) if provider else (received_lp_tokens / (self.pool.lp_tokens + received_lp_tokens)), # new share of this provider
                    'present_balance_A': wallet_A.available, # present user balance of currency_A
                    'present_balance_B': wallet_B.available, # present user balance of currency_B
                    'after_balance_A': wallet_A.available - attrs['amount_A'], # user balance of currency_A after this transaction
                    'after_balance_B': wallet_B.available - necessary_amount_B, # user balance of currency_B after this transaction
                    'pool_price': pool_price, # current pool price
                    'pool_amount_A': self.pool.amount_A, # current pool amount_A
                    'pool_amount_B': self.pool.amount_B # current pool amount_B
                }
            elif attrs['type'] == 'remove': # user want decrease liquidity
                if attrs['remove_percent'] == 0:
                    raise exceptions.ParseError(
                        self.error_messages['remove_percent_cant_be_zero'], 'remove_percent_cant_be_zero'
                    )
                if not self.pool.lp_tokens:
                    raise exceptions.ParseError(
                        self.error_messages['pool_is_empty'], 'pool_is_empty'
                    )
                provider = Provider.objects.find_by_user_pool(self.user, self.pool)
                if not provider or not provider.lp_tokens:
                    raise exceptions.ParseError(
                        self.error_messages['you_dont_have_liquidity'], 'you_dont_have_liquidity'
                    )
                returned_list = provider.remove_liquidity(attrs['remove_percent'], update_pool=False) # pre removing
                received_amount_A = returned_list[0] # the amount_A that user will receive (with this remove_percent)
                received_amount_B = returned_list[1] # the amount_B that user will receive (with this remove_percent)
                burn_lp_tokens = returned_list[2] # lp_tokens that user will be lose

                wallet_A = Wallet.objects.find_by_currency_symbol_and_merge_to_last(self.user, attrs['currency_A_symbol'])
                wallet_B = Wallet.objects.find_by_currency_symbol_and_merge_to_last(self.user, attrs['currency_B_symbol'])
                return {
                    'type': attrs['type'],
                    'amount_A': received_amount_A,
                    'amount_B': received_amount_B,
                    'new_amount_A': received_amount_A + provider.get_amount_A(), # new amount_A of this provider
                    'new_amount_B': received_amount_B + provider.get_amount_B(), # new amount_B of this provider
                    'new_share': (provider.lp_tokens - burn_lp_tokens) / (self.pool.lp_tokens - burn_lp_tokens), # new share of this provider
                    'present_balance_A': wallet_A.available, # present user balance of currency_A
                    'present_balance_B': wallet_B.available, # present user balance of currency_B
                    'after_balance_A': wallet_A.available + received_amount_A, # user balance of currency_A after this transaction
                    'after_balance_B': wallet_B.available + received_amount_B, # user balance of currency_B after this transaction
                    'pool_price': self.pool.cal_price() if not self.is_reverse else (1 / self.pool.cal_price()), # current pool price
                    'pool_amount_A': self.pool.amount_A, # current pool amount_A
                    'pool_amount_B': self.pool.amount_B # current pool amount_B
                }

        if self.pool.suspend_providing is True:
            raise exceptions.ParseError(
                self.error_messages['pool_is_suspended_for_now'], 'pool_is_suspended_for_now'
            )
        return attrs

    def create(self, validated_data):
        pool_price = self.pool.cal_price()
        if pool_price != -1:
            currencies_price_class = CurrenciesPrice()
            necessary_amount_B = pool_price * validated_data['amount_A']
            necessary_amount_B_value_USDT = currencies_price_class.cal_value_in_usdt(validated_data['currency_B_symbol'], necessary_amount_B)
            currency_B_value_USDT = currencies_price_class.cal_value_in_usdt(validated_data['currency_B_symbol'], validated_data['amount_B'])
            if not math.isclose(necessary_amount_B_value_USDT, currency_B_value_USDT, abs_tol=0.1): # check if value of currency_A is almost equal to value of currency_B or not
                raise exceptions.ParseError({
                    "status": False,
                    "message": _(f"برای تامین نقدینگی مقدار {validated_data['amount_A']} {validated_data['currency_A_symbol']} باید مقدار {necessary_amount_B} {validated_data['currency_B_symbol']} وارد استخر نقدینگی کنید")
                })
        else: # pool is empty and we can't get price of that, so we get price from global markets
            currencies_price_class = CurrenciesPrice()
            currency_A_value_USDT = currencies_price_class.cal_value_in_usdt(validated_data['currency_A_symbol'], validated_data['amount_A'])
            currency_B_value_USDT = currencies_price_class.cal_value_in_usdt(validated_data['currency_B_symbol'], validated_data['amount_B'])
            necessary_amount_B = currency_A_value_USDT / (currency_B_value_USDT / validated_data['amount_B'])
            if not math.isclose(currency_A_value_USDT, currency_B_value_USDT, abs_tol=0.1): # check if value of currency_A is almost equal to value of currency_B or not
                raise exceptions.ParseError({
                    "status": False,
                    "message": _(f"برای تامین نقدینگی مقدار {validated_data['amount_A']} {validated_data['currency_A_symbol']} باید مقدار {necessary_amount_B} {validated_data['currency_B_symbol']} وارد استخر نقدینگی کنید")
                })
        wallet_A = Wallet.objects.find_by_currency_symbol_and_merge_to_last(self.user, validated_data['currency_A_symbol'])
        wallet_B = Wallet.objects.find_by_currency_symbol_and_merge_to_last(self.user, validated_data['currency_B_symbol'])
        if not wallet_A.check_available_balance(validated_data['amount_A']): # check user wallet_A balance
            raise exceptions.ParseError({
                "status": False,
                "message": _(f"موجودی {wallet_A.excurrency.currency.name_fa} شما کافی نمیباشد")
            })
        if not wallet_B.check_available_balance(necessary_amount_B): # check user wallet_B balance
            raise exceptions.ParseError({
                "status": False,
                "message": _(f"موجودی {wallet_B.excurrency.currency.name_fa} شما کافی نمیباشد")
            })
        wallet_A.low_balance(validated_data['amount_A']) # low_balance of wallet_A
        wallet_B.low_balance(necessary_amount_B) # low_balance of wallet_B

        user_provider = Provider.objects.find_by_user_pool(self.user, self.pool)
        if user_provider: # user already is a provider
            first_lp_tokens = user_provider.lp_tokens
            user_provider.add_liquidity(validated_data['amount_A'], necessary_amount_B)
            lp_tokens_difference = user_provider.lp_tokens - first_lp_tokens
        else: # user first providing
            user_provider = Provider.objects.create_new_provider(
                user=self.user,
                pool=self.pool,
                amount_A=validated_data['amount_A'],
                amount_B=necessary_amount_B
            )
            lp_tokens_difference = user_provider.lp_tokens
        
        # create new transaction
        ProviderHistory.objects.create_new_tx(
            provider=user_provider,
            type='add',
            amount_A=validated_data['amount_A'],
            amount_B=necessary_amount_B,
            lp_tokens_difference=lp_tokens_difference,
            lp_tokens_pool=user_provider.pool.lp_tokens
        )

        # show more information
        providing_ser = ProvidingSerializers(user_provider, many=False, context={"request": self.context.get('request')}).data
        providing_ser['type'] = 'add'
        providing_ser['amount_A'] = validated_data['amount_A']
        providing_ser['amount_B'] = necessary_amount_B
        providing_ser['new_amount_A'] = user_provider.get_amount_A()
        providing_ser['new_amount_B'] = user_provider.get_amount_B()
        providing_ser['new_share'] = user_provider.get_share()
        providing_ser['present_balance_A'] = wallet_A.available
        providing_ser['present_balance_B'] = wallet_B.available
        providing_ser['pool_price'] = self.pool.cal_price()
        providing_ser['pool_amount_A'] = self.pool.amount_A
        providing_ser['pool_amount_B'] = self.pool.amount_B
        return providing_ser

    def update(self, instance, validated_data):
        # remove liquidity
        if validated_data['remove_percent'] == 0:
            raise exceptions.ParseError(
                self.error_messages['remove_percent_cant_be_zero'], 'remove_percent_cant_be_zero'
            )
        if not instance.lp_tokens:
            raise exceptions.ParseError(
                self.error_messages['you_dont_have_liquidity'], 'you_dont_have_liquidity'
            )
        returned_list = instance.remove_liquidity(validated_data['remove_percent'])
        received_amount_A = returned_list[0] # the amount_A that user will receive (with this remove_percent)
        received_amount_B = returned_list[1] # the amount_B that user will receive (with this remove_percent)
        burn_lp_tokens = returned_list[2] # lp_tokens that user will be lose

        wallet_A = Wallet.objects.find_by_currency_symbol_and_merge_to_last(self.user, validated_data['currency_A_symbol']) # old version
        wallet_B = Wallet.objects.find_by_currency_symbol_and_merge_to_last(self.user, validated_data['currency_B_symbol']) # old version
        wallet_A.add_balance(received_amount_A, add_net=False)
        wallet_B.add_balance(received_amount_B, add_net=False)

        ProviderHistory.objects.create_new_tx( # create new transaction
            provider=instance,
            type='remove',
            amount_A=received_amount_A,
            amount_B=received_amount_B,
            lp_tokens_difference=burn_lp_tokens,
            lp_tokens_pool=instance.pool.lp_tokens,
        )

        # show more information
        providing_ser = ProvidingSerializers(instance, many=False, context={"request": self.context.get('request')}).data
        providing_ser['type'] = 'remove'
        providing_ser['amount_A'] = received_amount_A
        providing_ser['amount_B'] = received_amount_B
        providing_ser['new_amount_A'] = instance.get_amount_A()
        providing_ser['new_amount_B'] = instance.get_amount_B()
        providing_ser['new_share'] = instance.get_share()
        providing_ser['present_balance_A'] = wallet_A.available
        providing_ser['present_balance_B'] = wallet_B.available
        providing_ser['pool_price'] = self.pool.cal_price()
        providing_ser['pool_amount_A'] = self.pool.amount_A
        providing_ser['pool_amount_B'] = self.pool.amount_B

        return providing_ser
    

class ProviderHistorySerializers(serializers.ModelSerializer):
    """
    show provider transactions
    """
    time = serializers.SerializerMethodField('get_time', read_only=True)
    user_id = serializers.SerializerMethodField('get_user_id', read_only=True)

    class Meta:
        model = ProviderHistory
        fields = (
            'user_id',
            'type',
            'amount_A',
            'amount_B',
            'equivalent_irt',
            'equivalent_usdt',
            'equivalent_btc',
            'time'
        )

    def get_time(self, obj):
        """
        convert time to jalali
        """
        user_history_jalali_time = JalaliDatetime(datetime.strptime(str(obj.time), '%Y-%m-%d %H:%M:%S.%f%z').astimezone(tz=TehranTimezone())).isoformat().split("T")
        user_history_time = user_history_jalali_time[1].split(".")[0].split(":")
        return [user_history_jalali_time[0], f"{user_history_time[0]}:{user_history_time[1]}"]

    def get_user_id(self, obj):
        return obj.provider.user.id

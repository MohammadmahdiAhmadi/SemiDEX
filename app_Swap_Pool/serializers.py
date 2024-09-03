from rest_framework import serializers, exceptions
from rest_framework_simplejwt import authentication
from django.utils.translation import ugettext_lazy as _
from datetime import datetime, timedelta
import pytz

from app_Currency.models import Currency
from app_Swap_Pool.models import Pool
from app_Swap_Providing.models import Provider, ProviderHistory
from app_Swap_Providing.serializers import ProviderSerializers
from app_Swap_Swaping.models import SwapHistory


class CurrencySerializer(serializers.ModelSerializer):
    """
    serialized currency model
    """
    class Meta:
        model = Currency
        fields = (
            'name_fa',
            'name_en',
            'symbol',
            'logoimage',
        )

    def get_logoimage(self, obj):
        request = self.context.get("request")
        host = request.get_host()
        protocol = request.build_absolute_uri().split(host)[0]
        protocol = protocol.replace("http", "https") if protocol.split(":")[0] == "http" else protocol
        website_url = protocol + host
        return website_url + obj.logoimage.url


class PoolsDetailSerializers(serializers.ModelSerializer):
    """
    show some reports and information of pools
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
    }

    currency_A = CurrencySerializer(many=False, read_only=True)
    currency_B = CurrencySerializer(many=False, read_only=True)

    class Meta:
        model = Pool
        fields = (
            'id',
            'currency_A',
            'currency_B',
            'amount_A',
            'amount_B',
            'rank',
            'suspend_swap',
            'suspend_providing'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['id'].read_only = False
        self.fields['id'].required = False

    def validate(self, attrs):
        self.user = None
        request = self.context["request"]
        if request and hasattr(request, "user"):
            self.user = authentication.JWTAuthentication().authenticate(request)[0]
        if self.user is None:
            raise exceptions.ParseError(
                self.error_messages['user_does_not_exists'], 'user_does_not_exists'
            )

        pools = Pool.objects.all() if not attrs.get('id') else Pool.objects.filter_by_id(attrs['id']) # show all pools info if didn't get id else show just pool with this id
        if not pools:
            raise exceptions.ParseError(
                self.error_messages['pool_does_not_exists'], 'pool_does_not_exists'
            )

        pools_serializer = PoolsDetailSerializers(pools, many=True, context=self.context).data # serializing some data like amount_A, amount_B, rank, ...
        for index, pool_serializer in enumerate(pools_serializer): # add some extra information
            user_providing = Provider.objects.find_by_user_pool(user=self.user, pool=pools[index]) # get user provider object for this pool
            pool_serializer['user_info'] = ProviderSerializers(user_providing, many=False).data # serialize user provider object
            pool_serializer['price'] = pools[index].cal_price() # this pool price based on currency_B
            pool_serializer['total_value_locked'] = pools[index].cal_total_value_locked(base_currency=None) # based on currency_B
            pool_serializer['total_value_locked_irt'] = pools[index].cal_total_value_locked(base_currency='IRT') # based on IRT
            pool_serializer['total_value_locked_usdt'] = pools[index].cal_total_value_locked(base_currency='USDT') # based on USDT
            pool_serializer['total_value_locked_btc'] = pools[index].cal_total_value_locked(base_currency='BTC') # based on BTC
            pool_serializer['total_received_fees_irt'] = SwapHistory.objects.cal_total_received_fees(pool=pools[index], base_currency='IRT') # based on IRT
            last_24h_swaps = SwapHistory.objects.find_by_pool_time(start_date=datetime.now(tz=pytz.utc) - timedelta(days=1), end_date=datetime.now(tz=pytz.utc), pool=pools[index]) # get last 24 hours swap
            volume_24h_irt = 0
            for swap in last_24h_swaps: # sum volume of last 24 hours swap based on IRT
                volume_24h_irt += swap.input_amount * Pool.objects.cal_price(swap.input_currency.symbol, 'IRT')
            pool_serializer['volume_24h_irt'] = volume_24h_irt
            last_7d_swaps = SwapHistory.objects.find_by_pool_time(start_date=datetime.now(tz=pytz.utc) - timedelta(days=7), end_date=datetime.now(tz=pytz.utc), pool=pools[index]) # get last 7 days swap
            volume_7d_irt = 0
            for swap in last_7d_swaps: # sum volume of last 7 days swap based on IRT
                volume_7d_irt += swap.input_amount * Pool.objects.cal_price(swap.input_currency.symbol, 'IRT')
            pool_serializer['volume_7d_irt'] = volume_7d_irt
            # Chart

        return pools_serializer


class PoolsCurrenciesSerializers(serializers.Serializer):
    """
    show some reports of a currency in all pools
    """
    currency = serializers.SerializerMethodField('get_currency', read_only=True)
    tvl = serializers.SerializerMethodField('get_tvl', read_only=True)
    tvl_irt = serializers.SerializerMethodField('get_tvl_irt', read_only=True)
    volume_24h_irt = serializers.SerializerMethodField('get_volume_24h_irt', read_only=True)
    change_price_percent_24h = serializers.SerializerMethodField('get_change_price_percent_24h', read_only=True)
    total_received_fees = serializers.SerializerMethodField('get_total_received_fees', read_only=True)
    total_received_fees_irt = serializers.SerializerMethodField('get_total_received_fees_irt', read_only=True)
    price_irt = serializers.SerializerMethodField('get_price_irt', read_only=True)
    pools_pairs = serializers.SerializerMethodField('get_pools_pairs', read_only=True)

    currency_symbol = serializers.CharField(required=True, write_only=True) # get currency symbol

    def get_currency(self, obj):
        """
        :return: serilizing currency information
        """
        currency = Currency.objects.find_by_symbol(obj['currency_symbol'])
        return CurrencySerializer(currency, many=False).data

    def get_tvl(self, obj):
        """
        :return: total value locked of this currency on all pools based on itself
        """
        return Pool.objects.cal_total_value_locked_currency_in_all_pools(currency_symbol=obj['currency_symbol'], base_currency=None)

    def get_tvl_irt(self, obj):
        """
        :return: total value locked of this currency on all pools based on IRT
        """
        return Pool.objects.cal_total_value_locked_currency_in_all_pools(currency_symbol=obj['currency_symbol'], base_currency='IRT')

    def get_volume_24h_irt(self, obj):
        """
        :return: sum volume of last 24 hours swap based on IRT in all pools
        """
        sum = 0
        pools = Pool.objects.filter_by_currency(currency_symbol=obj['currency_symbol'].upper())
        for pool in pools:
            last_24h_swaps = SwapHistory.objects.find_by_pool_time(start_date=datetime.now(tz=pytz.utc) - timedelta(days=1), end_date=datetime.now(tz=pytz.utc), pool=pool)
            for swap in last_24h_swaps:
                # if swap.input_currency.symbol.upper() == obj['currency_symbol'].upper():
                sum += swap.input_amount * Pool.objects.cal_price(swap.input_currency.symbol, 'IRT')
        return sum
    
    def get_change_price_percent_24h(self, obj):
        """
        :return: percentage of price changes in the last 24 hours based on irt
        """
        if obj['currency_symbol'].upper() == 'IRT':
            return 0
        current_price = Pool.objects.cal_price(obj['currency_symbol'].upper(), 'IRT')
        pool = Pool.objects.find_by_currencies_symbol(obj['currency_symbol'].upper(), 'IRT', is_reverse=True)[0]
        last_24h_swap = SwapHistory.objects.find_by_pool_time(start_date=datetime.now(tz=pytz.utc) - timedelta(days=1), end_date=datetime.now(tz=pytz.utc), pool=pool).filter(input_currency__symbol=obj['currency_symbol'].upper()).last()
        if not last_24h_swap:
            return 0
        last_24h_price = last_24h_swap.after_price
        return (current_price - last_24h_price) / last_24h_price

    def get_total_received_fees(self, obj):
        """
        :return: total received fees based on this currency in all pools
        """
        return SwapHistory.objects.cal_total_received_fees_currency_in_all_pools(currency_symbol=obj['currency_symbol'], base_currency=None)['amount']

    def get_total_received_fees_irt(self, obj):
        """
        :return: total received fees based on IRT in all pools
        """
        return SwapHistory.objects.cal_total_received_fees_currency_in_all_pools(currency_symbol=obj['currency_symbol'], base_currency='IRT')['value']

    def get_price_irt(self, obj):
        """
        :return: this currency price based on IRT
        """
        return Pool.objects.cal_price(currency_symbol=obj['currency_symbol'].upper(), base_currency_symbol='IRT')

    def get_pools_pairs(self, obj):
        """
        :return: all pools that have this currency on one side
        """
        pools = Pool.objects.filter_by_currency(currency_symbol=obj['currency_symbol'].upper())
        pairs = []
        for pool in pools:
            pairs.append({"pool_id": pool.id, "currency_A_symbol": pool.currency_A.symbol, "currency_B_symbol": pool.currency_B.symbol})
        return pairs


class HomeSerializers(serializers.Serializer):
    """
    show some report and information in home page
    """
    tvl_irt = serializers.SerializerMethodField('get_tvl_irt', read_only=True)
    change_tvl_percent_24h = serializers.SerializerMethodField('get_change_tvl_percent_24h', read_only=True)
    total_received_fees_irt = serializers.SerializerMethodField('get_total_received_fees_irt', read_only=True)
    volume_24h_irt = serializers.SerializerMethodField('get_volume_24h_irt', read_only=True)
    change_volume_percent_48h_24h = serializers.SerializerMethodField('get_change_volume_percent_48h_24h', read_only=True)

    def get_tvl_irt(self, obj):
        """
        :return: tvl of all pools based on IRT
        """
        pools = Pool.objects.all()
        sum = 0
        for pool in pools:
            sum += pool.cal_total_value_locked(base_currency='IRT')
        return sum

    def get_change_tvl_percent_24h(self, obj):
        """
        :return: ratio of present_tvl and last_24h_tvl
        """
        present_tvl = self.get_tvl_irt(obj) # get present tvl
        pools = Pool.objects.all()
        last_24h_tvl = 0
        for pool in pools:
            last_24h_providing = ProviderHistory.objects.find_by_pool_time(start_date=datetime.now(tz=pytz.utc) - timedelta(days=1), end_date=datetime.now(tz=pytz.utc), pool=pool).last()
            if last_24h_providing:
                last_24h_tvl += last_24h_providing.cal_pool_total_value_locked(base_currency='IRT') # calculating tvl using ProviderHistory object based IRT (we save pool data on every providing transactions)
        return (present_tvl - last_24h_tvl) / last_24h_tvl if last_24h_tvl != 0 else 0

    def get_total_received_fees_irt(self, obj):
        """
        :return: total received fees in all pools based on IRT
        """
        pools = Pool.objects.all()
        sum = 0
        for pool in pools:
            fees = SwapHistory.objects.cal_total_received_fees(pool=pool, base_currency='IRT')
            sum += fees['total_value']
        return sum

    def get_volume_24h_irt(self, obj):
        """
        :return: volume of all swaps amount in last 24 hours in all pools based on IRT
        """
        last_24h_swaps = SwapHistory.objects.find_by_pool_time(start_date=datetime.now(tz=pytz.utc) - timedelta(days=1), end_date=datetime.now(tz=pytz.utc), pool=None)
        sum = 0
        for swap in last_24h_swaps:
            sum += swap.input_amount * Pool.objects.cal_price(swap.input_currency.symbol, 'IRT')
        return sum

    def get_change_volume_percent_48h_24h(self, obj):
        """
        :return: ratio of the day before yesterday volume (-48, -24) and past day volume (-24, now) in all pools
        """
        last_24h_swaps = SwapHistory.objects.find_by_pool_time(start_date=datetime.now(tz=pytz.utc) - timedelta(days=1), end_date=datetime.now(tz=pytz.utc), pool=None)
        sum_24h = 0 # past day volume
        for swap in last_24h_swaps:
            sum_24h += swap.input_amount * Pool.objects.cal_price(swap.input_currency.symbol, 'IRT')
        last_48h_24h_swaps = SwapHistory.objects.find_by_pool_time(start_date=datetime.now(tz=pytz.utc) - timedelta(days=2), end_date=datetime.now(tz=pytz.utc) - timedelta(days=1), pool=None)
        sum_48h_24h = 0 # past 2 day volume
        for swap in last_48h_24h_swaps:
            sum_48h_24h += swap.input_amount * Pool.objects.cal_price(swap.input_currency.symbol, 'IRT')
        if sum_48h_24h == 0: # there is no swap in the day before yesterday
            return 0
        return (sum_24h - sum_48h_24h) / sum_48h_24h

from django.db import models
from django.utils import timezone

from app_Admin_Option.models import Option
from app_User.models import User
from app_Swap_Pool.models import Pool
from app_Currency.models import Currency


class SwapHistoryManager(models.Manager):
    def find_by_id(self, id):
        return self.filter(id=id).first()

    def find_by_pool(self, pool):
        """
        find all swaps of this pool
        """
        return self.filter(pool=pool)
    
    def find_by_user_pool_last(self, user=None, pool=None):
        """
        find all swaps of this user in this pool and order_by last to first
        """
        if user:
            return self.filter(user=user, pool=pool).order_by('-time') if pool else self.filter(user=user).order_by('-time')
        else:
            return self.filter(pool=pool).order_by('-time') if pool else self.all().order_by('-time')

    def find_by_pool_time(self, start_date, end_date, pool=None):
        """
        find all swaps in certain time range [start_date, end_date] in this pool
        """
        return self.filter(pool=pool, time__range=(start_date, end_date)).order_by('-time') if pool else self.filter(time__range=(start_date, end_date)).order_by('-time')

    def cal_total_received_fees(self, pool, base_currency=None):
        """
        calculating total received fees based on base_currency in this pool
        """
        swap_query = self.find_by_pool(pool=pool) # all swaps of this pool
        fees = {'currency_A': 0, 'currency_B': 0, 'total_value': 0}
        for swap in swap_query:
            if swap.input_currency.symbol.upper() == swap.pool.currency_A.symbol.upper(): # fee that we received, is in currency_B
                fees['currency_B'] += swap.fee_amount
            else: # fee that we received, is in currency_A
                fees['currency_A'] += swap.fee_amount
        if base_currency is None: # return total value based on currency_B
            fees['total_value'] = fees['currency_B'] + fees['currency_A'] * pool.cal_price()
        elif base_currency == 'IRT' or base_currency == 'USDT' or base_currency == 'BTC': # return total value based on base_currency
            currency_A_value = fees['currency_A'] * Pool.objects.cal_price(currency_symbol=pool.currency_A.symbol.upper(), base_currency_symbol=base_currency)
            currency_B_value = fees['currency_B'] * Pool.objects.cal_price(currency_symbol=pool.currency_B.symbol.upper(), base_currency_symbol=base_currency)
            fees['total_value'] = currency_A_value + currency_B_value
        return fees

    def cal_total_received_fees_currency_in_all_pools(self, currency_symbol, base_currency=None):
        """
        calculating total received fees of this currency_symbol based on base_currency in all pools
        """
        pools = Pool.objects.filter_by_currency(currency_symbol) # all pools with this currency_symbol
        fees={'amount': 0, 'value': 0}
        for pool in pools:
            swap_query = self.find_by_pool(pool=pool) # all swaps of this pool
            for swap in swap_query:
                if swap.output_currency.symbol.upper() == currency_symbol.upper():
                    fees['amount'] += swap.fee_amount
        if base_currency is None: # return total value based on currency_symbol
            fees['value'] = fees['amount']
        elif base_currency == 'IRT' or base_currency == 'USDT' or base_currency == 'BTC': # return total value based on base_currency
            fees['value'] = fees['amount'] * Pool.objects.cal_price(currency_symbol.upper(), base_currency_symbol=base_currency)
        return fees

    def create_new_swap(self, user, pool, input_currency, output_currency, input_amount, output_amount, fee_amount, before_price, after_price, slippage_tolerance):
        """
        create new swap transaction history
        """
        fee_total_option = Option.objects.find_by_code_name('swap_fee')
        return self.create(
            user=user,
            pool=pool,
            input_currency=input_currency,
            output_currency=output_currency,
            input_amount=input_amount,
            output_amount=output_amount,
            fee_amount=fee_amount,
            fee_percentage=float(fee_total_option.value),
            fee_value_irt=fee_amount * Pool.objects.cal_price(output_currency.symbol, 'IRT'),
            before_price=before_price,
            after_price=after_price,
            slippage_tolerance=slippage_tolerance,
            equivalent_irt=output_amount * Pool.objects.cal_price(currency_symbol=output_currency.symbol, base_currency_symbol='IRT'),
            equivalent_usdt=output_amount * Pool.objects.cal_price(currency_symbol=output_currency.symbol, base_currency_symbol='USDT'),
            equivalent_btc=output_amount * Pool.objects.cal_price(currency_symbol=output_currency.symbol, base_currency_symbol='BTC'),
        )


class SwapHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=True, related_name='SwapHistory_User')
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, default=True, related_name='SwapHistory_Pool')
    input_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, default=True, related_name='SwapHistory_input_currency')
    output_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, default=True, related_name='SwapHistory_output_currency')
    input_amount = models.FloatField(null=True, blank=True, default=0)
    output_amount = models.FloatField(null=True, blank=True, default=0)
    fee_amount = models.FloatField(null=True, blank=True, default=0)
    fee_percentage = models.FloatField(null=True, blank=True, default=0)
    fee_value_irt = models.FloatField(null=True, blank=True, default=0)
    before_price = models.FloatField(null=True, blank=True, default=0)
    after_price = models.FloatField(null=True, blank=True, default=0)
    slippage_tolerance = models.FloatField(null=True, blank=True, default=0)
    equivalent_irt = models.FloatField(null=True, blank=True, default=0)
    equivalent_usdt = models.FloatField(null=True, blank=True, default=0)
    equivalent_btc = models.FloatField(null=True, blank=True, default=0)
    time = models.DateTimeField(default=timezone.now)
    
    objects = SwapHistoryManager()

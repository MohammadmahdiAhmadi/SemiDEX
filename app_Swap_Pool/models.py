from django.db import models
from django.utils import timezone
from django.db.models import Q
import math

from app_Admin_Option.models import Option
from app_Currency.models import Currency
from app_Utils.classes import CurrenciesPrice


class PoolManager(models.Manager):
    def find_by_id(self, id):
        """
        :params id: id of pool
        :return: pool object with this id
        """
        return self.filter(id=id).first()

    def filter_by_id(self, id):
        """
        :params id: id of pool
        :return: pool object list with this id (because i need list of an object except an object!)
        """
        return self.filter(id=id)

    def find_by_currencies(self, currency_A, currency_B):
        """
        :params currency_A: currency_A object
        :params currency_B: currency_B object
        :return: the pool with this currencies
        """
        return self.filter(currency_A=currency_A, currency_B=currency_B).first()

    def filter_by_currency(self, currency_symbol):
        """
        :params currency_symbol: one side currency symbol
        :return: all pools that this currency is in one side of them
        """
        return self.filter(Q(currency_A__symbol=currency_symbol) | Q(currency_B__symbol=currency_symbol))

    def find_by_currencies_symbol(self, currency_A_symbol, currency_B_symbol, is_reverse=False):
        """
        :params currency_A_symbol: currency_A symbol
        :params currency_B_symbol: currency_B symbol
        :params is_reverse: if is_reverse is True, we search currency_A in side B and currency_B in side A too
        :return: 
        """
        pool = self.filter(currency_A__symbol=currency_A_symbol, currency_B__symbol=currency_B_symbol).first()
        if not is_reverse:
            return [pool, False]
        else:
            return [pool, False] if (pool is not None) else [self.filter(currency_A__symbol=currency_B_symbol, currency_B__symbol=currency_A_symbol).first(), True]

    def create_new_pool(self, currency_A, currency_B, rank):
        """
        create new pool if it does not already exist
        """
        pool = self.find_by_currencies(currency_A, currency_B)
        if not pool:
            self.create(currency_A=currency_A, currency_B=currency_B, rank=rank)
            return True
        return False

    def find_currencies_symbol(self):
        """
        :return: all currencies that exist in pools
        """
        pools = self.all()
        currencies_symbol = []
        for pool in pools:
            if pool.currency_A.symbol not in currencies_symbol:
                currencies_symbol.append(pool.currency_A.symbol)
            if pool.currency_B.symbol not in currencies_symbol:
                currencies_symbol.append(pool.currency_B.symbol)
        return currencies_symbol
    
    def cal_total_value_locked_currency_in_all_pools(self, currency_symbol, base_currency=None):
        """
        :param currency_symbol: symbol of the currency that we want calculate tvl of that in all pools
        :param base_currency: value based on this currency (currency_symbol, IRT, USDT, BTC)
        :return: tvl in all pools
        """
        pools = self.filter_by_currency(currency_symbol.upper()) # get all pools with this currency (currency_A or currency_B)
        total_amount = 0
        for pool in pools: # sum all amount in all pools
            total_amount = total_amount + pool.amount_A if pool.currency_A.symbol.upper() == currency_symbol.upper() else total_amount + pool.amount_B
        if base_currency is None: # return total_amount
            return total_amount
        elif base_currency.upper() == 'IRT' or base_currency.upper() == 'USDT' or base_currency.upper() == 'BTC':
            return total_amount * Pool.objects.cal_price(currency_symbol=currency_symbol.upper(), base_currency_symbol=base_currency.upper()) # convert value to base_currency
        else:
            return -1

    def cal_price(self, currency_symbol, base_currency_symbol):
        """
        :params currency_symbol: currency symbol that i want it price
        :params base_currency_symbol: currency symbol that i want calculating price based on it
        :return: currency_symbol price based on base_currency_symbol
        """
        currencies_price_class = CurrenciesPrice()
        if base_currency_symbol == 'IRT': # based on IRT
            if currency_symbol == 'IRT':
                return 1
            irt_pools = self.filter_by_currency(currency_symbol='IRT') # get all pools that one side of them is IRT
            for irt_pool in irt_pools: # search in irt pools for find currency_symbol in other side (like BTC-IRT)
                if irt_pool.currency_A.symbol == currency_symbol: # currency_A is currency_symbol
                    price = irt_pool.cal_price(is_reverse=False) # we shouldn't reverse that
                    if price > 0:
                        return price
                elif irt_pool.currency_B.symbol == currency_symbol: # currency_B is currency_symbol
                    price = irt_pool.cal_price(is_reverse=True) # we should reverse that
                    if price > 0:
                        return price
            return currencies_price_class.cal_value_in_irt(currency_symbol, 1) # there is no pool with this currency and we received price from our redis price list based on IRT
        elif base_currency_symbol == 'USDT': # based on USDT
            if currency_symbol == 'USDT':
                return 1
            usdt_pools = self.filter_by_currency(currency_symbol='USDT') # get all pools that one side of them is USDT
            for usdt_pool in usdt_pools: # search in usdt pools for find currency_symbol in other side (like USDT-DAI)
                if usdt_pool.currency_A.symbol == currency_symbol: # currency_A is currency_symbol
                    price = usdt_pool.cal_price(is_reverse=False) # we shouldn't reverse that
                    if price > 0:
                        return price
                elif usdt_pool.currency_B.symbol == currency_symbol: # currency_B is currency_symbol
                    price = usdt_pool.cal_price(is_reverse=True) # we should reverse that
                    if price > 0:
                        return price
            return currencies_price_class.cal_value_in_usdt(currency_symbol, 1) # there is no pool with this currency and we received price from our redis price list based on USDT
        elif base_currency_symbol == 'BTC': # based on BTC
            if currency_symbol == 'BTC':
                return 1
            btc_pools = self.filter_by_currency(currency_symbol='BTC') # get all pools that one side of them is BTC
            for btc_pool in btc_pools: # search in btc pools for find currency_symbol in other side (like BTC-ETH)
                if btc_pool.currency_A.symbol == currency_symbol: # currency_A is currency_symbol
                    price = btc_pool.cal_price(is_reverse=False) # we shouldn't reverse that
                    if price > 0:
                        return price
                elif btc_pool.currency_B.symbol == currency_symbol: # currency_B is currency_symbol
                    price = btc_pool.cal_price(is_reverse=True) # we should reverse that
                    if price > 0:
                        return price
            return currencies_price_class.cal_value_in_btc(currency_symbol, 1) # there is no pool with this currency and we received price from our redis price list based on BTC
        else:
            return -1


class Pool(models.Model):
    currency_A = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='Pool_currency_A')
    currency_B = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='Pool_currency_B')
    amount_A = models.FloatField(null=False, blank=False, default=0.0)
    amount_B = models.FloatField(null=False, blank=False, default=0.0)
    lp_tokens = models.FloatField(null=False, blank=False, default=0.0)
    rank = models.IntegerField(null=False, blank=False, default=1)
    suspend_swap = models.BooleanField(default=False, null=False)
    suspend_providing = models.BooleanField(default=False, null=False)
    time = models.DateTimeField(default=timezone.now)

    objects = PoolManager()

    def suspend(self, swap_or_providing=None):
        """
        set suspend_swap and suspend_providing True. then users can't providing or swaping in this pool
        """
        if swap_or_providing is None: # both
            self.suspend_swap = True
            self.suspend_providing = True
        elif swap_or_providing == 'swap': # suspend_swap
            self.suspend_swap = True
        elif swap_or_providing == 'providing': # suspend_providing
            self.suspend_providing = True
        return self.save()

    def increase_liquidity(self, amount_A, amount_B):
        self.amount_A += amount_A
        self.amount_B += amount_B
        return self.save()

    def decrease_liquidity(self, amount_A, amount_B):
        self.amount_A -= amount_A
        self.amount_B -= amount_B
        return self.save()
    
    def increase_lp_tokens(self, lp_tokens):
        self.lp_tokens += lp_tokens
        return self.save()

    def decrease_lp_tokens(self, lp_tokens):
        self.lp_tokens -= lp_tokens
        return self.save()

    def cal_total_value_locked(self, base_currency=None, amount_A=None, amount_B=None):
        """
        :params base_currency: if it is None, we calculate tvl based on currency_B. that can be IRT, USDT, BTC too
        :params amount_A: if it is None, we calculate tvl based on self.amount_A
        :params amount_B: if it is None, we calculate tvl based on self.amount_B
        :return: calculate total value locked in pool (currency_A value + currency_B value)
        """
        amount_A = self.amount_A if (amount_A is None or amount_B is None) else amount_A
        amount_B = self.amount_B if (amount_A is None or amount_B is None) else amount_B
        if base_currency is None:
            pool_price = self.cal_price()
            return (pool_price * amount_A) + amount_B
        elif base_currency == 'IRT' or base_currency == 'USDT' or base_currency == 'BTC':
            currency_A_value = amount_A * Pool.objects.cal_price(currency_symbol=self.currency_A.symbol, base_currency_symbol=base_currency)
            currency_B_value = amount_B * Pool.objects.cal_price(currency_symbol=self.currency_B.symbol, base_currency_symbol=base_currency)
            return currency_A_value + currency_B_value
        else:
            return -1

    def cal_price(self, is_reverse=False):
        """
        :params is_reverse: if it's False, we calculating price based on currency_B and if it's True, we calculating price based on currency_A
        :return: amount ratio of two currencies
        """
        if is_reverse:
            return self.amount_A / self.amount_B if self.amount_B != 0 else -1
        else:
            return self.amount_B / self.amount_A if self.amount_A != 0 else -1

    def cal_constant(self):
        """
        :return: cal constant (based on formula x * y = k)
        """
        return self.amount_A * self.amount_B

    def cal_swaping_amount_to_equating(self, currency_symbol, amount):
        """
        :params currency_symbol: currency_symbol
        :params amount: amount of this currency that we want swaping
        :return: swaping amount; if we swap in this amount, our remain amount of this currency and receive amount of other side currecny are have same value
        we calculating this based on a complex math formula
        """
        fee_option = Option.objects.find_by_code_name('swap_fee')
        fee_factor = (1 - fee_option.value)

        pool_amount = self.amount_A if currency_symbol == self.currency_A.symbol else self.amount_B

        A = (pool_amount * (1 + fee_factor)) / (2 * fee_factor)
        return A * (-1 + math.sqrt(1 + ((pool_amount * amount) / (fee_factor * (A*A))))) # math formula


    def swaping(self, input_amount, is_reverse=False, update_pool=False):
        """
        :params input_amount: input amount of currency
        :params is_reverse: if it's False, input is for currency_A, if it's True, input is for currency_B
        :params update_pool: if it's True, thats mean we are in real swaping not pre swaping
        :return: calculating output amount, fee, slippage tolerance and final price based on (x * y = k) formula
        """
        option_total_fee = Option.objects.find_by_code_name('swap_fee') # all fee that we received per swap
        option_providers_fee = Option.objects.find_by_code_name('swap_providers_fee') # all providers fee that we received per swap
        if is_reverse: # input is for currency_B
            new_amount_B = self.amount_B + input_amount * (1 - float(option_total_fee.value)) # new amount_B in pool (after adding the input amount and reducing the fee)
            new_amount_A = self.cal_constant() / new_amount_B # new amount_A in pool (based on new amount_B)
            final_amount_B = self.amount_B + input_amount * (1 - (float(option_total_fee.value) - float(option_providers_fee.value))) # final amount_B in pool (after adding the input amount and seprating exchange fee and providers fee)
            final_amount_A = new_amount_A # final amount_A in pool (== new_amount_A)
            final_price = final_amount_A / final_amount_B # calculating final price with new amounts
            output_amount = self.amount_A - new_amount_A # output amount is old amount_A - new amount_A
            fee_amount = new_amount_A - (self.cal_constant() / (self.amount_B + input_amount)) # calculating amount of fee that we received (that is, if we did not receive a fee, how much will remain in the pool and how much is left now ?!)
            slippage_tolerance = 1 - (final_price / self.cal_price(is_reverse=True)) # how much percent does this swap change the price?
        else: # input is for currency_A
            new_amount_A = self.amount_A + input_amount * (1 - float(option_total_fee.value)) # new amount_A in pool (after adding the input amount and reducing the fee)
            new_amount_B = self.cal_constant() / new_amount_A # new amount_B in pool (based on new amount_A)
            final_amount_A = self.amount_A + input_amount * (1 - (float(option_total_fee.value) - float(option_providers_fee.value))) # final amount_A in pool (after adding the input amount and seprating exchange fee and providers fee)
            final_amount_B = new_amount_B # final amount_B in pool (== new_amount_B)
            final_price = final_amount_B / final_amount_A # calculating final price with new amounts
            output_amount = self.amount_B - new_amount_B # output amount is old amount_B - new amount_B
            fee_amount = new_amount_B - (self.cal_constant() / (self.amount_A + input_amount)) # calculating amount of fee that we received (that is, if we did not receive a fee, how much will remain in the pool and how much is left now ?!)
            slippage_tolerance = 1 - (final_price / self.cal_price(is_reverse=False)) # how much percent does this swap change the price?
        
        if update_pool: # this is real swap not pre swap
            self.amount_A = final_amount_A
            self.amount_B = final_amount_B
            self.save()
            
        return {
            'output_amount': output_amount,
            'fee_amount': fee_amount,
            'slippage_tolerance': slippage_tolerance,
            'final_price': final_price
        }


class PoolHistoryManager(models.Manager):
    def find_by_id(self, id):
        return self.filter(id=id).first()

    def snapshot_of_pools(self):
        """
        :return: save pool information at this time
        """
        pools = Pool.objects.all()
        for pool in pools:
            self.create(
                pool=pool,
                amount_A=pool.amount_A,
                amount_B=pool.amount_B,
                lp_tokens=pool.lp_tokens,
                price_A_irt=Pool.objects.cal_price(currency_symbol=pool.currency_A.symbol, base_currency_symbol='IRT'),
                price_B_irt=Pool.objects.cal_price(currency_symbol=pool.currency_B.symbol, base_currency_symbol='IRT'),
                price_A_usdt=Pool.objects.cal_price(currency_symbol=pool.currency_A.symbol, base_currency_symbol='USDT'),
                price_B_usdt=Pool.objects.cal_price(currency_symbol=pool.currency_B.symbol, base_currency_symbol='USDT'),
                price_A_btc=Pool.objects.cal_price(currency_symbol=pool.currency_A.symbol, base_currency_symbol='BTC'),
                price_B_btc=Pool.objects.cal_price(currency_symbol=pool.currency_B.symbol, base_currency_symbol='BTC'),
            )


class PoolHistory(models.Model):
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, default=True, related_name='PoolHistory_Pool')
    amount_A = models.FloatField(null=False, blank=False, default=0.0)
    amount_B = models.FloatField(null=False, blank=False, default=0.0)
    lp_tokens = models.FloatField(null=False, blank=False, default=0.0)
    price_A_irt = models.FloatField(null=False, blank=False, default=0.0)
    price_B_irt = models.FloatField(null=False, blank=False, default=0.0)
    price_A_usdt = models.FloatField(null=False, blank=False, default=0.0)
    price_B_usdt = models.FloatField(null=False, blank=False, default=0.0)
    price_A_btc = models.FloatField(null=False, blank=False, default=0.0)
    price_B_btc = models.FloatField(null=False, blank=False, default=0.0)
    time = models.DateTimeField(default=timezone.now)

    objects = PoolHistoryManager()

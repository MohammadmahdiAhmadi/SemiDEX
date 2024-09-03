from django.db import models
from django.utils import timezone
import math

from app_User.models import User
from app_Swap_Pool.models import Pool


class ProviderManager(models.Manager):
    def find_by_id(self, id):
        return self.filter(id=id).first()

    def find_by_user(self, user):
        """
        :return: find all provider objects of this user
        """
        return self.filter(user=user).order_by('pool__rank')

    def find_by_user_pool(self, user, pool):
        """
        :return: find this user provider object for this pool
        """
        return self.filter(user=user, pool=pool).first()
    
    def find_by_pool(self, pool):
        """
        :return: find all provider objects of this pool
        """
        return self.filter(pool=pool).order_by('pool__rank')

    def find_pool_by_user(self, user, only_has_liquidity=False):
        """
        :param only_has_liquidity: if it's True, we only return objects that have liquidity
        :return: find all pool objects that this user activating them before
        """
        user_providing = self.filter(user=user, lp_tokens__gt=0).order_by('pool__rank') if only_has_liquidity else self.filter(user=user).order_by('pool__rank')
        user_pools = []
        for providing in user_providing:
            user_pools.append(providing.pool)
        return {'user_pools': user_pools, 'user_providing': user_providing}

    def create_new_provider(self, user, pool, amount_A, amount_B):
        lp_tokens_received = math.sqrt(amount_A * amount_B)
        new_provider = self.create(
            user=user,
            pool=pool,
            lp_tokens=lp_tokens_received,
        )
        new_provider.pool.increase_liquidity(amount_A, amount_B)
        new_provider.pool.increase_lp_tokens(lp_tokens_received)
        return new_provider


class Provider(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=True, related_name='Provider_User')
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, default=True, related_name='Provider_Pool')
    lp_tokens = models.FloatField(null=False, blank=False, default=0.0)
    time = models.DateTimeField(default=timezone.now)

    objects = ProviderManager()


    def get_share(self):
        """
        :return: get current share bases on provider lp tokens and pool lp tokens
        """
        return (self.lp_tokens / self.pool.lp_tokens) if self.pool.lp_tokens else 0

    def get_amount_A(self):
        return (self.lp_tokens / self.pool.lp_tokens) * self.pool.amount_A if self.pool.lp_tokens else 0 # calculating provider amount_A based on user share and pool amount

    def get_amount_B(self):
        return (self.lp_tokens / self.pool.lp_tokens) * self.pool.amount_B if self.pool.lp_tokens else 0 # calculating provider amount_B based on user share and pool amount
        
    def add_liquidity(self, amount_A, amount_B):
        received_lp_tokens = math.sqrt(amount_A * amount_B) # calculating lp tokens that's provider will receive (sqrt(x*y))
        self.lp_tokens += received_lp_tokens
        self.pool.lp_tokens += received_lp_tokens
        self.pool.amount_A += amount_A
        self.pool.amount_B += amount_B
        self.pool.save()
        return self.save()

    def remove_liquidity(self, share, update_pool=True):
        """
        :params share: share of liquidity that we want remove
        :params update_pool: if it's True, thats mean we are in real remove liquidity not pre remove liquidity
        :return: received_amount_A, received_amount_B, burn_lp_tokens
        """
        if self.lp_tokens:
            burn_lp_tokens = self.lp_tokens * share
            received_amount_A = self.pool.amount_A * (burn_lp_tokens / self.pool.lp_tokens)
            received_amount_B = self.pool.amount_B * (burn_lp_tokens / self.pool.lp_tokens)
            if update_pool:
                self.lp_tokens -= burn_lp_tokens
                self.pool.lp_tokens -= burn_lp_tokens
                self.pool.amount_A -= received_amount_A
                self.pool.amount_B -= received_amount_B
                self.pool.save()
                self.save()
            return [received_amount_A, received_amount_B, burn_lp_tokens]


class ProviderHistoryManager(models.Manager):
    def find_by_id(self, id):
        return self.filter(id=id).first()

    def find_by_provider(self, provider):
        """
        :param provider: find first history of this provider
        :return: find first provider history
        """
        return self.filter(provider=provider).order_by('time').first()

    def find_by_last(self, pool_id=None):
        """
        :param pool_id: the pool_id that we want receive history of that
        :return: descending list of all transaction of this pool
        """
        if not pool_id:
            return self.all().order_by('-time')
        else:
            # Bad Algorithm
            all = self.all().order_by('-time')
            result = []
            for provider_transaction in all:
                if provider_transaction.provider.pool.id == pool_id:
                    result.append(provider_transaction)
            return result
    
    def find_by_pool_time(self, start_date, end_date, pool=None):
        """
        :param start_date: datetime object
        :param end_date: datetime object
        :param pool: if is None, return history of all pools
        :return: all history in [start_date, end_date] time range
        """
        return self.filter(provider__pool=pool, time__range=(start_date, end_date)).order_by('-time') if pool else self.filter(time__range=(start_date, end_date)).order_by('-time')

    def create_new_tx(self, provider, type, amount_A, amount_B, lp_tokens_difference, lp_tokens_pool):
        """
        :return: create new transaction
        """
        return self.create(
            provider=provider,
            type=type,
            amount_A=amount_A,
            amount_B=amount_B,
            lp_tokens_difference=lp_tokens_difference,
            lp_tokens_pool=lp_tokens_pool,
            equivalent_irt = amount_A * Pool.objects.cal_price(currency_symbol=provider.pool.currency_A.symbol, base_currency_symbol='IRT') + amount_B * Pool.objects.cal_price(currency_symbol=provider.pool.currency_B.symbol, base_currency_symbol='IRT'),
            equivalent_usdt = amount_A * Pool.objects.cal_price(currency_symbol=provider.pool.currency_A.symbol, base_currency_symbol='USDT') + amount_B * Pool.objects.cal_price(currency_symbol=provider.pool.currency_B.symbol, base_currency_symbol='USDT'),
            equivalent_btc = amount_A * Pool.objects.cal_price(currency_symbol=provider.pool.currency_A.symbol, base_currency_symbol='BTC') + amount_B * Pool.objects.cal_price(currency_symbol=provider.pool.currency_B.symbol, base_currency_symbol='BTC')
        )


class ProviderHistory(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, default=True, related_name='ProviderHistory_Provider')
    type_choices = [('add', 'add'), ('remove', 'remove')]
    type = models.CharField(max_length=6, choices=type_choices, default='add')
    amount_A = models.FloatField(null=True, blank=True)
    amount_B = models.FloatField(null=True, blank=True)
    lp_tokens_pool = models.FloatField(null=False, blank=False, default=0.0)
    lp_tokens_difference = models.FloatField(null=False, blank=False, default=0.0)
    equivalent_irt = models.FloatField(null=True, blank=True, default=0)
    equivalent_usdt = models.FloatField(null=True, blank=True, default=0)
    equivalent_btc = models.FloatField(null=True, blank=True, default=0)
    time = models.DateTimeField(default=timezone.now)

    objects = ProviderHistoryManager()

    def cal_pool_total_value_locked(self, base_currency=None):
        """
        :param base_currency: value calculating based on this currency
        :return: tvl of this pool at the time of this transaction
        """
        if self.type == 'add':
            if self.lp_tokens_pool == self.lp_tokens_difference: # first transaction
                pool_amount_A = self.amount_A
                pool_amount_B = self.amount_B
            else:
                before_share = self.lp_tokens_difference / (self.lp_tokens_pool - self.lp_tokens_difference) # share percent of this lp_token before transaction
                pool_amount_A = (self.amount_A / before_share) + self.amount_A # pool amount_A after this transaction
                pool_amount_B = (self.amount_B / before_share) + self.amount_B # pool amount_B after this transaction
            return self.provider.pool.cal_total_value_locked(base_currency, pool_amount_A, pool_amount_B) # call cal_total_value_locked with specific amounts
        else:
            before_share = self.lp_tokens_difference / (self.lp_tokens_pool + self.lp_tokens_difference) # share percent of this lp_token before transaction
            pool_amount_A = (self.amount_A / before_share) - self.amount_A # pool amount_A after this transaction
            pool_amount_B = (self.amount_B / before_share) - self.amount_B # pool amount_B after this transaction
            return self.provider.pool.cal_total_value_locked(base_currency, pool_amount_A, pool_amount_B) # call cal_total_value_locked with specific amounts

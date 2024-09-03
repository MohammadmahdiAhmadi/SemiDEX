from django.core.management.base import BaseCommand
from app_Currency.models import Currency
from app_Swap_Pool.models import Pool

class Command(BaseCommand):
    help = 'Initial A New Pool'

    def add_arguments(self, parser):
        parser.add_argument('currency_A', type=str, help='currency_A symbol') # BTC for example
        parser.add_argument('currency_B', type=str, help='currency_A symbol') # USDT for example

    def handle(self, *args, **options):
        currency_A = Currency.objects.find_by_symbol(options['currency_A'].upper())
        currency_B = Currency.objects.find_by_symbol(options['currency_B'].upper())
        if not currency_A:
            return f'{options["currency_A"]} does not exist'
        if not currency_B:
            return f'{options["currency_B"]} does not exist'
        last_pool = Pool.objects.order_by('-rank').first()
        rank = 1 if last_pool is None else last_pool.rank # set rank of this pool
        pool = Pool.objects.create_new_pool(currency_A=currency_A, currency_B=currency_B, rank=rank)
        if pool:
            return f'pool {options["currency_A"]}-{options["currency_B"]} created'
        else:
            return f'pool {options["currency_A"]}-{options["currency_B"]} could not create'

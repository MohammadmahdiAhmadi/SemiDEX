from django.core.management.base import BaseCommand
from app_Swap_Pool.models import Pool

class Command(BaseCommand):
    help = 'Suspend Providing In This Pool'

    def add_arguments(self, parser):
        parser.add_argument('pool_id', type=int, help='pool id')

    def handle(self, *args, **options):
        pool = Pool.objects.find_by_id(id=options["pool_id"])
        if pool:
            pool.suspend('providing')
            return f'providing in pool {pool.currency_A.symbol}-{pool.currency_B.symbol} is suspend now'
        else:
            return f'pool with id {options["pool_id"]} does not exist'

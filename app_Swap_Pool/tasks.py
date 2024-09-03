from celery import shared_task

from app_Swap_Pool.models import PoolHistory


@shared_task()
def SnapshotPoolHistory():
    PoolHistory.objects.snapshot_of_pools()

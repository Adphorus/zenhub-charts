from celery.schedules import crontab
from celery.task import periodic_task

from boards.fetcher.fetch import Fetcher
from boards.models import Repo


@periodic_task(run_every=crontab(minute=0, hour='*/3'),  # every 3 hours
               name='Periodic data update')
def fetch():
    repos = Repo.objects.all()
    for repo in repos:
        fetcher = Fetcher([repo.name])
        fetcher.sync()

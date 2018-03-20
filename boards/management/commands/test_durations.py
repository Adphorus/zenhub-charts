from django.core.management.base import BaseCommand

from boards.fetcher.fetch import Fetcher
from boards.models import Issue


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '-r', '--repo',
            type=str,
            dest='repo_name',
            required=False
        )

        parser.add_argument(
            '-i', '--issue',
            type=int,
            dest='issue_number',
            required=True
        )

    def handle(self, *args, **options):
        fetcher = Fetcher()
        issue = Issue.objects.get(
            repo__name=options['repo_name'],
            number=options['issue_number']
        )
        for transfer in issue.transfers.order_by('transfered_at'):
            print(transfer)
        print(fetcher.calculate_durations(issue))

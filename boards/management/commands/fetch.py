from django.core.management.base import BaseCommand
from django.conf import settings

from boards.fetcher.clients import GithubClient, ZenhubClient
from boards.fetcher.fetch import Fetcher
from boards.models import Repo


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--initial',
            action='store_true',
            dest='initial',
            default=False
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            dest='fix',
            default=False
        )

    def handle(self, *args, **options):
        self.github = GithubClient(**settings.GITHUB)
        self.zenhub = ZenhubClient(**settings.ZENHUB)

        if options['initial']:
            print(
                'It seems like this is your first installation.\n'
                'Please fill in your repository names to fetch.'
            )
            raw_repos = input('Repository names separated by commas: ')
            repo_names = raw_repos.split(',')
            for repo_name in repo_names:
                github_repo = self.github.get_repo(repo_name)
                Repo.objects.create(
                    repo_id=github_repo['id'],
                    name=github_repo['name']
                )
                print('created ', github_repo['name'])

        repos = Repo.objects.all()
        for repo in repos:
            fetcher = Fetcher(
                [repo.name],
                initial=options['initial'],
                fix=options['initial'] or options['fix']
            )
            fetcher.sync()

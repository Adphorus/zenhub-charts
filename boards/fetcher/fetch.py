import logging
from django.utils.timezone import now
from django.conf import settings
from django.db.models.fields import DateTimeField

from boards.fetcher.clients import GithubClient, ZenhubClient
from boards.fetcher.exceptions import PipelineNotFoundError
from boards.models import (
    Repo, Pipeline, PipelineNameMapping, Issue, Transfer
)

logger = logging.getLogger(__name__)


class Fetcher(object):
    closed_pipeline_name = 'Closed'

    def __init__(self, repo_names=None, initial=False, fix=False):
        self.repo_names = repo_names
        self.initial = initial
        self.fix = fix
        self.github = GithubClient(**settings.GITHUB)
        self.zenhub = ZenhubClient(**settings.ZENHUB)
        self.pipelines = {}

    def create_pipelines(self, repo, pipelines):
        Pipeline.objects.get_or_create(
            pipeline_id=f"{repo}-closed",
            name=self.closed_pipeline_name, repo=repo,
            defaults={
                'order': 10000  # assuming there is no board with 10000 cols
            }
        )

        for order, pipeline in enumerate(pipelines):
            by_id = Pipeline.objects.filter(
                repo=repo, pipeline_id=pipeline['id'])
            if by_id.exists() and by_id.first().name != pipeline['name']:
                # Name changed
                PipelineNameMapping.objects.create(
                    repo=repo,
                    old_name=by_id.first().name,
                    new_name=pipeline['name']
                )
                by_id.update(name=pipeline['name'])
            else:
                Pipeline.objects.update_or_create(
                    pipeline_id=pipeline['id'],
                    name=pipeline['name'], repo=repo,
                    defaults={
                        'order': order
                    }
                )
        self.pipelines = self.get_pipelines(repo)
        self.first_pipeline = Pipeline.objects.filter(
            repo=repo).earliest('order')
        self.pipeline_name_mapping = dict(PipelineNameMapping.objects.filter(
            repo=repo
        ).values_list('old_name', 'new_name'))

    def get_pipelines(self, repo):
        return {
            p.name: p
            for p in Pipeline.objects.filter(repo=repo)
        }

    def get_issue_numbers(self, pipelines):
        return [
            item['issue_number']
            for sublist in [i['issues'] for i in pipelines]
            for item in sublist
        ]

    def close_issues(
            self, repo, current_issue_numbers, remote_issue_numbers, extra=[]):
        must_be_closed = list(
            set(current_issue_numbers) - set(remote_issue_numbers)
        )
        must_be_closed += extra
        must_be_closed = set(must_be_closed)
        closed_pipeline = self.pipelines[self.closed_pipeline_name]
        issues_to_close = Issue.objects.filter(
            repo=repo,
            number__in=must_be_closed
        ).exclude(latest_pipeline_name=self.closed_pipeline_name)
        total = len(issues_to_close)
        for counter, issue in enumerate(issues_to_close, 1):
            github_issue = self.github.get_issue(issue.repo.name, issue.number)
            closed_at = github_issue['closed_at']
            if not closed_at:
                logger.info(
                    f'No closed_at info for #{issue.number} in {repo}'
                )
                continue 
            latest_pipeline = Transfer.objects.filter(
                issue__number=issue.number
            ).latest('transfered_at').to_pipeline
            if issue.latest_pipeline_name != self.closed_pipeline_name:
                issue.latest_pipeline_name = self.closed_pipeline_name
                issue.save()
            if latest_pipeline != closed_pipeline:
                kwargs = {
                    'issue': issue,
                    'from_pipeline': latest_pipeline,
                    'to_pipeline': closed_pipeline,
                    'transfered_at': closed_at,
                }
                self.create_transfer(**kwargs)
                logger.info(
                    f'#{issue.number} in {repo} is closed '
                    f'{counter}/{total}'
                )
            issue.durations = self.calculate_durations(issue)
            issue.save(update_fields=['durations'])

    def stupid_django_datetime_hack(self, value):
        """
        Django does not call `to_python` on model save,
        so any `DateField` or `DateTimeField` returns string instead.
        """
        return DateTimeField().to_python(value)

    def create_transfer(
            self, issue, from_pipeline, to_pipeline, transfered_at):
        transfer, created = Transfer.objects.get_or_create(
            issue=issue,
            from_pipeline=from_pipeline,
            to_pipeline=to_pipeline,
            transfered_at=transfered_at
        )
        if created:
            logger.info(f'created transfer: {transfer}')
            issue.latest_pipeline_name = transfer.to_pipeline.name
            issue.latest_transfer_date = transfered_at
            issue.save()

    def get_pipeline(self, repo, name):
        def select_one(pipeline_names):
            try:
                selected_index = int(input('Select one: '))
                return pipeline_names[selected_index]
            except ValueError:
                print('Input an integer value')
            except IndexError:
                print('Pipeline not in the list')
            except:
                print('An error occured')
            return select_one(pipeline_names)

        try:
            return self.pipelines[self.pipeline_name_mapping.get(name, name)]
        except KeyError:
            if self.fix:
                print(
                    f'\n\nCould not find "{name}" on the "{repo}" board. '
                    'These are the options:'
                )
                pipeline_names = list(self.pipelines.keys())
                for index, pipeline in enumerate(pipeline_names):
                    print(f'[{index}]: {pipeline}')
                new_name = select_one(pipeline_names)
                PipelineNameMapping.objects.create(
                    repo=repo, old_name=name, new_name=new_name
                )
                self.pipelines[new_name] = self.pipelines[new_name]
                self.pipeline_name_mapping[name] = new_name
                return self.pipelines[new_name]
            else:
                raise PipelineNotFoundError(repo, name)

    def get_issue_events(self, repo, issue_number):
        github_issue = self.github.get_issue(repo.name, issue_number)
        zenhub_issue_events = self.zenhub.get_issue_events(
            repo.repo_id, issue_number)
        labels = [i['name'] for i in github_issue['labels']]
        issue, created = Issue.objects.update_or_create(
            repo=repo, number=issue_number,
            defaults={
                'title': github_issue['title'],
                'latest_transfer_date': github_issue['created_at'],
                'labels': labels,
            }
        )
        transfers = [
            i for i in zenhub_issue_events if i['type'] == 'transferIssue']
        if created:
            # No transfers yet, but the issue is created
            # and it is in the first pipeline of the board
            # Use `issue.created_at` as the first date
            created_at = self.stupid_django_datetime_hack(
                issue.latest_transfer_date)
            Transfer.objects.get_or_create(
                issue=issue,
                to_pipeline=self.first_pipeline,
                transfered_at=github_issue['created_at']
            )
            issue.latest_pipeline_name = self.first_pipeline.name
            duration = (now() - created_at).total_seconds()
            issue.durations[self.first_pipeline.name] = duration
            issue.save()
        # create the oldest ones first, otherwise
        # we can not calculate durations
        transfers = sorted(transfers, key=lambda x: x['created_at'])
        for transfer in transfers:
            kwargs = {
                'issue': issue,
                'from_pipeline': (
                    self.get_pipeline(repo, transfer['from_pipeline']['name'])
                ),
                'to_pipeline': self.get_pipeline(
                    repo, transfer['to_pipeline']['name']),
                'transfered_at': transfer['created_at']
            }
            self.create_transfer(**kwargs)
        durations = self.calculate_durations(issue)
        issue.durations = durations
        issue.save(update_fields=['durations'])

    def calculate_durations(self, issue):
        transfers = issue.transfers.select_related(
            'from_pipeline', 'to_pipeline').order_by('transfered_at')
        durations = {}
        last_index = transfers.count() - 1
        for order, transfer in enumerate(transfers):
            previous = None
            if order>0:
                previous = transfers[order-1]
            if not previous or not previous.to_pipeline:
                continue
            delta =  transfer.transfered_at - previous.transfered_at
            if not previous.to_pipeline.name in durations:
                durations[previous.to_pipeline.name] = 0
            durations[previous.to_pipeline.name] += delta.total_seconds()
            if order == last_index:
                if transfer.to_pipeline.name != self.closed_pipeline_name:
                    delta = now() - transfer.transfered_at
                    total_seconds = delta.total_seconds()
                else:
                    total_seconds = 0
                if not transfer.to_pipeline.name in durations:
                    durations[transfer.to_pipeline.name] = 0
                durations[transfer.to_pipeline.name] += total_seconds
        logger.info(f'calculated durations')
        return durations

    def get_closed_issue_numbers_from_github(self, repo):
        closed_github_issue_numbers = []
        if self.fix:
            pages = self.github.get_issues(
                repo=repo.name, iterate=True, assignee='*', state='closed')
            for page in pages:
                for issue in page:
                    closed_github_issue_numbers.append(issue['number'])
        return closed_github_issue_numbers

    def sync(self):
        repos = Repo.objects.all()
        if self.repo_names:
            repos = repos.filter(name__in=self.repo_names)
        for repo in repos:
            current_issues = repo.issues.all()
            board = self.zenhub.get_board(repo.repo_id)
            self.create_pipelines(repo, board['pipelines'])
            closed_github_issue_numbers = \
                self.get_closed_issue_numbers_from_github(repo)
            remote_issue_numbers = self.get_issue_numbers(board['pipelines'])
            remote_issue_numbers += closed_github_issue_numbers
            current_issue_numbers = current_issues.values_list(
                'number', flat=True)
            total = len(remote_issue_numbers)
            for counter, issue_number in enumerate(remote_issue_numbers, 1):
                logger.info(
                    f'Getting issue events for #{issue_number} in {repo} '
                    f'{counter}/{total}')    
                self.get_issue_events(repo, issue_number)
            self.close_issues(
                repo,
                current_issue_numbers,
                remote_issue_numbers,
                extra=closed_github_issue_numbers
            )

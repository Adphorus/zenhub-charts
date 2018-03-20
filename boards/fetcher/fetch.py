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
        self.closed_pipeline, created = Pipeline.objects.get_or_create(
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
        zenhub_issue = self.zenhub.get_issue(repo.repo_id, issue_number)
        latest_pipeline_name = zenhub_issue['pipeline']['name']
        closed = latest_pipeline_name == self.closed_pipeline_name
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
            self._prepare_transfer(issue, e) for e in zenhub_issue_events
            if e['type'] == 'transferIssue'
        ]
        transfers = sorted(transfers, key=lambda x: x['transfered_at']) 
        transfers.insert(0, {
            'issue': issue, 
            'transfered_at': github_issue['created_at'],
            'from_pipeline': None,
            'to_pipeline': self.first_pipeline,
        })
        if closed:
            # Issue is closed, we can not get this info from Zenhub
            transfers.append({
                'issue': issue,
                'transfered_at': github_issue['closed_at'],
                'from_pipeline': transfers[-1]['to_pipeline'],
                'to_pipeline': self.closed_pipeline,
            })
        for transfer in transfers:
            self.create_transfer(**transfer)
        durations = self.calculate_durations(issue)
        issue.durations = durations
        issue.latest_transfer_date = transfers[-1]['transfered_at']
        issue.latest_pipeline_name = latest_pipeline_name
        issue.save()

    def _prepare_transfer(self, issue, transfer):
        _transfer = {'issue': issue, 'transfered_at': transfer['created_at']}
        from_pipeline_name = transfer.get('from_pipeline', {}).get('name')
        if from_pipeline_name:
            _transfer['from_pipeline'] = self.get_pipeline(
                issue.repo, from_pipeline_name)
        to_pipeline_name = transfer.get('to_pipeline', {}).get('name')
        if to_pipeline_name:
            _transfer['to_pipeline'] = self.get_pipeline(
                issue.repo, to_pipeline_name)
        return _transfer

    def create_transfer(
            self, issue, from_pipeline, to_pipeline, transfered_at):
        if from_pipeline == to_pipeline:
            return
        transfer, created = Transfer.objects.get_or_create(
            issue=issue,
            from_pipeline=from_pipeline,
            to_pipeline=to_pipeline,
            transfered_at=transfered_at
        )
        if created:
            logger.info(f'created transfer: {transfer}')

    def calculate_durations(self, issue):
        transfers = issue.transfers.select_related(
            'from_pipeline', 'to_pipeline').order_by('transfered_at')
        durations = {}
        last_index = transfers.count() - 1
        for order, transfer in enumerate(transfers):
            if order == last_index:
                if transfer.to_pipeline.name != self.closed_pipeline_name:
                    delta = now() - transfer.transfered_at
                    total_seconds = delta.total_seconds()
                    if not transfer.to_pipeline.name in durations:
                        durations[transfer.to_pipeline.name] = 0
                    durations[transfer.to_pipeline.name] += total_seconds
            previous = None
            if order > 0:
                previous = transfers[order-1]
            if not previous or not previous.to_pipeline:
                continue
            delta =  transfer.transfered_at - previous.transfered_at
            if not previous.to_pipeline.name in durations:
                durations[previous.to_pipeline.name] = 0
            durations[previous.to_pipeline.name] += delta.total_seconds()
        
        logger.info(f'calculated durations')
        return durations

    def get_closed_issue_numbers(self, repo):
        closed_github_issue_numbers = []
        if self.fix:
            pages = self.github.get_issues(
                repo=repo.name, iterate=True, assignee='*', state='closed')
            for page in pages:
                for issue in page:
                    closed_github_issue_numbers.append(issue['number'])
        return closed_github_issue_numbers

    def get_issue_numbers(self, pipelines):
        return [
            item['issue_number']
            for sublist in [i['issues'] for i in pipelines]
            for item in sublist
        ]

    def sync(self):
        repos = Repo.objects.all()
        if self.repo_names:
            repos = repos.filter(name__in=self.repo_names)
        for repo in repos:
            current_issues = repo.issues.all()
            board = self.zenhub.get_board(repo.repo_id)
            self.create_pipelines(repo, board['pipelines'])
            closed_github_issue_numbers = self.get_closed_issue_numbers(repo)
            issue_numbers = self.get_issue_numbers(board['pipelines'])
            issue_numbers += closed_github_issue_numbers
            issue_numbers = sorted(list(set(issue_numbers)), reverse=True)
            total = len(issue_numbers)
            for counter, issue_number in enumerate(issue_numbers, 1):
                logger.info(
                    f'Getting issue events for #{issue_number} in {repo} '
                    f'{counter}/{total}')    
                self.get_issue_events(repo, issue_number)

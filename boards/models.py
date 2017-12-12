from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import JSONField


class Repo(models.Model):
    repo_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Pipeline(models.Model):
    name = models.CharField(max_length=255)
    repo = models.ForeignKey('Repo')
    pipeline_id = models.CharField(
        max_length=255)
    order = models.PositiveSmallIntegerField()

    def __str__(self):
        return self.name

    class Meta:
        unique_together = (('pipeline_id', 'repo', ), )


class PipelineNameMapping(models.Model):
    """
    Pipeline names might be changed sometime before.
    We can not track these changes.
    That's why we need to keep a mapping between
    old names and new names.
    """
    repo = models.ForeignKey('Repo')
    old_name = models.CharField(max_length=255)
    new_name = models.CharField(max_length=255)

    def __str__(self):
        return f'{self.old_name} -> {self.new_name}'


class Issue(models.Model):
    repo = models.ForeignKey('Repo', related_name='issues')
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    durations = JSONField(default=dict)
    latest_pipeline_name = models.CharField(max_length=255)
    latest_transfer_date = models.DateTimeField()

    def __str__(self):
        return f'{self.repo}/{self.title}/{self.number}'

    @property
    def github_url(self):
        owner = settings.GITHUB['owner']
        return (
            f'https://github.com/{owner}/{self.repo.name}'
            f'/issues/{self.number}'
        )

    class Meta:
        unique_together = (('repo', 'number'),)


class Transfer(models.Model):
    issue = models.ForeignKey('Issue', related_name='transfers')
    from_pipeline = models.ForeignKey(
        'Pipeline', related_name='from_transfers', null=True)
    to_pipeline = models.ForeignKey(
        'Pipeline', related_name='to_transfers', null=True)
    transfered_at = models.DateTimeField()

    def __str__(self):
        return (
            f'({self.issue}) {self.from_pipeline}'
            f' -> {self.to_pipeline} @ {self.transfered_at}'
        )

    class Meta:
        unique_together = (
            ('issue', 'from_pipeline', 'to_pipeline', 'transfered_at',),
        )

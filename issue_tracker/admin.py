from django.contrib import admin

from issue_tracker.models import (
    Repo, Issue, Pipeline, PipelineNameMapping, Transfer
)


admin.site.register(Repo)
admin.site.register(Issue)
admin.site.register(Pipeline)
admin.site.register(PipelineNameMapping)
admin.site.register(Transfer)

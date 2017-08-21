from datetime import datetime, timedelta
import statistics
from collections import defaultdict

from django.http import JsonResponse
from django.views import generic

from .models import Issue, Pipeline, Repo


class ChartView(generic.TemplateView):
    template_name = 'issue_tracker/chart.html'

    def get_context_data(self, *args, **kwargs):
        repo_name = self.request.GET.get('repo')
        repos = Repo.objects.values_list('name', flat=True)
        durations = self.request.GET.get('durations')
        durations = durations.split(',') if durations else []
        context = super(ChartView, self).get_context_data(*args, **kwargs)
        pipelines = Pipeline.objects.filter(
            repo__name=repo_name
        ).values_list('name', flat=True).order_by('order')
        context['pipelines'] = {i: i in durations for i in pipelines}
        context['repos'] = {i: i == repo_name for i in repos}
        return context


class ChartResponseView(generic.View):
    def get_chart_data(
            self, repo_name, since=None, until=None, durations=None):
        issues = Issue.objects.select_related('repo').filter(
            repo__name=repo_name,
        ).exclude(durations={})
        if since and until:
            since = self._py_datetime(int(float(since)))
            until = self._py_datetime(int(float(until)))
            issues = issues.filter(
                latest_transfer_date__gte=since,
                latest_transfer_date__lte=until
            )
        else:
            since = datetime.now() - timedelta(days=365)
            issues = issues.filter(
                latest_transfer_date__gte=since
            )
        if durations:
            issues = issues.filter(durations__has_any_keys=durations)
        issues = issues.order_by('latest_transfer_date')
        raw_data = defaultdict(list)
        pipelines = set()
        rolling_set = []
        deviation_set = []
        for order, issue in enumerate(issues):
            rolling, deviation = self.calculate_rolling_average(
                issues, order, durations)
            if rolling and deviation:
                rolling_set.append(rolling)
                deviation_set.append(deviation)
            pipelines.add(issue.latest_pipeline_name)
            total = sum([v for k, v in issue.durations.items()])
            pipelines_and_times = self.get_cycle_time_values(
                        issue, durations, only_values=False)
            raw_data[issue.latest_pipeline_name].append({
                'x': self._js_time(issue.latest_transfer_date.timestamp()),
                'y': self._js_time(total),
                'title': issue.title,
                'issue_number': issue.number,
                'url': issue.github_url,
                'durations': {
                    k: self._js_time(v)
                    for k, v in pipelines_and_times
                }
            })
        series = []
        series.append({
            'id': 'deviation',
            'name': 'Deviation',
            'data': deviation_set,
            'color': 'rgba(191, 227, 252, 0.1)',
            'type': 'arearange'})

        series.append({
            'id': 'average',
            'name': 'Average',
            'data': rolling_set,
            'color': 'rgba(19, 109, 168, 1)',
            'type': 'line'})

        duration_totals = [
            self._js_time(
                sum(self.get_cycle_time_values(i, durations))) for i in issues
        ]
        median = self.get_median(duration_totals)
        average = self.get_average(duration_totals)
        percentiles = self.get_percentiles(duration_totals)

        for key, data in raw_data.items():
            data = sorted(data, key=lambda x: x['x'])
            series.append({
                'id': key, 'name': key, 'data': data, 'type': 'scatter'
            })

        return {
            'series': series,
            'median': median,
            'average': average,
            'percentiles': percentiles,
            'pipelines': list(pipelines)
        }

    def get_cycle_time_values(
            self, issue, cycle_time_pipelines, only_values=True):
        if cycle_time_pipelines:
            if only_values:
                return [
                    v for k, v in issue.durations.items()
                    if k in cycle_time_pipelines
                ]
            else:
                return {
                    k: v for k, v in issue.durations.items()
                    if k in cycle_time_pipelines
                }.items()
        else:
            if only_values:
                return issue.durations.values()
            else:
                return issue.durations.items()

    def calculate_rolling_average(self, issues, order, cycle_time_pipelines):
        """
        http://tinyurl.com/yaybq6g9
        """
        frame = 9  # TODO: calculate actual frame
        issues_as_list = list(issues)  # optimize to have less queries
        total = len(issues_as_list)
        if order < frame // 2 or total - frame // 2 < order - 1:
            return None, None
        average_result = []
        deviation_result = []
        xaxis = self._js_time(
            issues_as_list[order].latest_transfer_date.timestamp()
        )
        filtered_issues = issues_as_list[order-(frame//2):order+(frame//2)+1]
        total = sum(
            [sum(self.get_cycle_time_values(i, cycle_time_pipelines))
                for i in filtered_issues]
        )
        average = total / (frame)
        average_result = [
            xaxis,
            self._js_time(average)
        ]
        deviations = sum([
            abs(sum(self.get_cycle_time_values(i, cycle_time_pipelines))
                - average)
            for i in filtered_issues
        ])
        mean_deviation = deviations / (frame)
        deviation_result = [
            xaxis,
            self._js_time(average - abs(mean_deviation)),
            self._js_time(average + abs(mean_deviation)),
        ]
        return average_result, deviation_result

    def get_median(self, totals):
        try:
            return statistics.median(totals)
        except statistics.StatisticsError:
            return 0

    def get_average(self, totals):
        total = len(totals)
        if total:
            return sum(totals) / total
        return 0

    def get_percentiles(self, totals):
        ordered = sorted(totals)
        total = len(ordered)
        percents = [0.25, 0.50, 0.75, 0.90]
        return [ordered[int(total*i)] for i in percents]

    def _js_time(self, ts):
        """
        Javascript timestamps works with milliseconds
        """
        return ts * 1000

    def _py_datetime(self, ts):
        return datetime.fromtimestamp(ts / 1000)

    def get(self, request, *args, **kwargs):
        repo_name = request.GET.get('repo')
        since = request.GET.get('since')
        until = request.GET.get('until')
        durations = request.GET.get('durations')
        durations = durations.split(',') if durations else None
        return JsonResponse(self.get_chart_data(
            repo_name, since, until, durations))

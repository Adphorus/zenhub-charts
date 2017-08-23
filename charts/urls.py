from django.conf.urls import url

from .views import ChartView, ChartResponseView


urlpatterns = [
    url(r'^$', ChartView.as_view(), name='chart'),  # we currently have only one chart
    url(r'^cycle-time/chart-data/$', ChartResponseView.as_view(), name='chart-data'),
]

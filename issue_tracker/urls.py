from django.conf.urls import url

from .views import ChartView, ChartResponseView


urlpatterns = [
    url(r'^$', ChartView.as_view(), name='chart'),
    url(r'^chart-data/$', ChartResponseView.as_view(), name='chart-data'),
]

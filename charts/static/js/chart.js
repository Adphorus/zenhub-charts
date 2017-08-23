var url = '/cycle-time/chart-data/';
var qs = new URLSearchParams(window.location.search);
var repo = qs.get('repo');
var durations = qs.get('durations');

var asDays = function(duration) {
  var days = parseInt(duration.asDays());
  if (days > 1) {
    return days + ' days';
  }
  else {
    return duration.humanize();
  }
}

var getPlotLine = function(id, value, title) {
  var duration = moment.duration(value); 
  var conf = {
    median: {
      color: 'red',
      text: 'Median (' + asDays(duration) + ')',
      align: 'left'
    },
    average: {
      color: 'green',
      text: 'Average (' + asDays(duration) + ')',
      align: 'left'
    },
    percentile: {
      color: 'gray',
      text: title + ' (' + asDays(duration) + ')',
      align: 'center'
    }
  };
  return {
    id: id,
    value: value,
    color: conf[id]['color'],
    dashStyle: 'shortdash',
    width: 2,
    label: {
      text: conf[id]['text'],
      align: conf[id]['align']
    }
  }
}

$.getJSON(url + window.location.search, function (data) {
  seriesIds = data.series_ids;
  var options = {
    colors: ['#ff00ff', '#00ffff', '#ff5fd7', '#00ff00', '#ff0000', '#d7005f', '#afafd7', '#af0087', '#af8700', '#d7d787', '#5f5faf', '#d7afaf', '#d75f00', '#8700af', '#005fd7', '#5fd700', '#af5f5f', '#afd7af', '#5f00d7', '#5faf5f', '#00d75f', '#d7ff5f', '#875f87', '#0087af', '#d75fff', '#87afff', '#5fd7ff', '#d787d7', '#87d7d7', '#ff87af', '#00af87', '#5f8787', '#87875f', '#af87ff', '#5fffd7', '#0000ff', '#87af00', '#87ffaf', '#afff87'],
    title: {
      text: 'Cycle Time Chart'
    },
    xAxis: {
      type: 'datetime',
      labels: {
        format: '{value:%Y-%b-%e}'
      },
      title: {
        enabled: false
      },
      events:{
        afterSetExtremes:function(){
          var since = this.min;
          var until = this.max;
          var endpoint = URI(url);
          endpoint.setSearch('repo', repo);
          endpoint.setSearch('since', since);
          endpoint.setSearch('until', until);
          endpoint.setSearch('durations', durations);
          $.getJSON(endpoint,
            function(newData){
              this.chart.yAxis[0].removePlotLine('percentile');
              this.chart.yAxis[0].addPlotLine(
                getPlotLine('percentile', newData.percentiles[0], '25%')
              );
              this.chart.yAxis[0].addPlotLine(
                getPlotLine('percentile', newData.percentiles[1], '50%')
              );
              this.chart.yAxis[0].addPlotLine(
                getPlotLine('percentile', newData.percentiles[2], '75%')
              );
              this.chart.yAxis[0].addPlotLine(
                getPlotLine('percentile', newData.percentiles[3], '90%')
              );
              this.chart.yAxis[0].removePlotLine('median');
              this.chart.yAxis[0].removePlotLine('average');
              this.chart.yAxis[0].addPlotLine(
                getPlotLine('median', newData.median)
              );
              this.chart.yAxis[0].addPlotLine(
                getPlotLine('average', newData.average)
              );
            }.bind(this));
        }
      }
    },
    yAxis: {
      labels: {
        formatter: function() {
          var duration = moment.duration(this.value);
          return asDays(duration);
        }
      },
      title: {
        enabled: false
      },
      plotLines: [
        getPlotLine('percentile', data.percentiles[0], '25%'), 
        getPlotLine('percentile', data.percentiles[1], '50%'),
        getPlotLine('percentile', data.percentiles[2], '75%'),
        getPlotLine('percentile', data.percentiles[3], '90%'),
        getPlotLine('median', data.median),
        getPlotLine('average', data.average)
      ],
      min: 0
    },
    legend: {
      enabled: true,
    },
    tooltip: {
      formatter: function(){
        var body = ''
        if (typeof(this.point) === 'undefined') {
          var duration = moment.duration(this.points[1].y);
          var low = moment.duration(this.points[0].point.low);
          var high = moment.duration(this.points[0].point.high);
          body += '<b>Rolling Average:</b> ' + asDays(duration)
          body += '<br/><b>Deviation:</b> ' + asDays(low) + ' to ' + asDays(high)
        } else {
          body += '<b>' + this.point.title + '</b><br/>';
          for (var pipeline in this.point.durations){
            if (!this.point.durations.hasOwnProperty(pipeline)){continue}
            var duration = moment.duration(this.point.durations[pipeline]);
            body += '<b>' + pipeline + '</b>:' + asDays(duration) + '<br/>'
          }
        }
        return body;
      },
    },
    plotOptions: {
      scatter: {
        marker: {
          radius: 5,
          states: {
            hover: {
              enabled: true,
              lineColor: 'rgb(100,100,100)'
            }
          }
        },
        states: {
          hover: {
            marker: {
              enabled: false
            }
          }
        }
      },
      line: {
        marker: {
          radius: 0,
          states: {
            hover: {
              enabled: false,
            }
          }
        },
        tooltip: {
          enabled: false
        }
      },
      series: {
        cursor: 'pointer',
        point: {
          events: {
            click: function() {
              window.open(this.url);
            }
          }
        },
        events: {
          legendItemClick: function () {
            return false;
          }
        } 
      }
    },
    series: data.series
  };

  Highcharts.stockChart('chart', options,
    function(chart){
      $('#repos').change(
        function() {
          var endpoint = URI(window.location.href);
          endpoint.setSearch('repo', $(this).val());
          window.location.href = endpoint;
        }
      );
      $('#pipeline-form').submit(
        function(e){
          e.preventDefault();
          var durations = [];
          if ($('#pipelines').val()){
            durations = $('#pipelines').val().join();
          }
          var endpoint = URI(window.location.href); 
          endpoint.setSearch('repo', $('#repos').val());
          endpoint.setSearch('durations', durations);
          window.location.href = endpoint;
        }
      );
    });
});
$('#pipelines').select2({dropdownCssClass: 'dropdown-inverse'});
$('#repos').select2({dropdownCssClass: 'dropdown-inverse'});

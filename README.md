# issues

A temporary repository for issue_tracker application until god goes online

![](https://raw.githubusercontent.com/Adphorus/issues/master/resources/chart.png?token=ABPmHqpoxk7Y29tVKlKuWlqMJrbO8KWbks5ZmtaMwA%3D%3D)

## Installation

Create virtualenv using python>=3.6

Install requirements:

```
pip install -r requirements/dev.txt
```

Create postgresql database:

```
createdb issue_tracker
```

Copy settings:

```
cp issues/settings_dev.py-dist issues/settings_dev.py
```

Specify settings module:

```
export DJANGO_SETTINGS_MODULE='issues.settings_dev'
```

(Better set and unset this in your virtualenv's `bin/activate` script)

Load Fixtures:

```
./manage.py loaddata fixtures/repos.json
./manage.py loaddata fixtures/pipeline_names.json
```


## Getting Issues from Github and Zenhub

It is currently a manual process

```
./manage.py shell

In [1]: from issue_tracker.fetcher.fetch import Fetcher

In [2]: f = Fetcher(repo_names=['Product'])

In [3]: f.sync()
```


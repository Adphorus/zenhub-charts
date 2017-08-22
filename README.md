# ZenHub Cycle Time Chart

ZenHub Cycle Time Chart let's you visualize cycle times on your ZenHub board.

![](https://raw.githubusercontent.com/Adphorus/issues/master/resources/chart.png?token=ABPmHqpoxk7Y29tVKlKuWlqMJrbO8KWbks5ZmtaMwA%3D%3D)

See the [blog post](http://blog.adphorus.com) for more detail.

## Installation

Install [Redis](https://redis.io/).

Create virtualenv using `python>=3.6`.

Install requirements:

```
pip install -r requirements/base.txt
```

Create postgresql database:

```
createdb issue_tracker
```

Run migrations

```
./manage.py migrate
```

### Development settings

Install requirements:

```
pip install -r requirements/dev.txt
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



## Configuration

In order to fetch issues from both `GitHub` and `ZenHub`, you need to specify your tokens.

* [Get your ZenHub token](https://dashboard.zenhub.io/#/settings)
* [Get your GitHub token](https://github.com/settings/tokens) (Select repo scope)

![repo](resources/github_scope.png)

```
GITHUB = {
    'token': '<your token>',
    'owner': '<Organization or user name>'
}
ZENHUB = {
    'token': '<your token>'
}
```


## Getting Issues from GitHub and ZenHub

It is currently a manual process

```
./manage.py fetch --initial
```

* **initial:** Run the command for the first time. It may ask you questions about pipeline name mappings. We can not track previous name changes, so you have to define them on the first run.
* **fix:** If `--initial` is specified, you do not need to give this parameter. This parameter let's us fetch previously closed issues.

### Periodic tasks

First of all configure your broker.

```
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis'
```

Then run Celery with beat (`-B`) support.


```
celery -A issues worker -B -l info
```

A periodic task will fetch new issues every 3 hours.

## Run the server

```
./manage.py runserver
```

Visit [http://localhost:8000](http://localhost:8000)

## Admin

In order to use the admin, run:

```
./manage.py createsuperuser
```

go to [http://localhost:8000/admin](http://localhost:8000/admin)

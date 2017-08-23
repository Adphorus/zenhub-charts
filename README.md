# ZenHub Cycle Time Chart

ZenHub Cycle Time Chart let's you visualize cycle times on your ZenHub board.

![](resources/chart.png)

See the [blog post](http://blog.adphorus.com) for more detail.

## Installation

Install [Redis](https://redis.io/) and [PostgreSQL](https://www.postgresql.org/). (This application is dependent on PostgreSQL's JSONB field.)

Create virtualenv using `python>=3.6`.

Install requirements:

```
pip install -r requirements/base.txt
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

### Extra settings

`settings.DEBUG` is `False` by default. But this won't allow serving static files with development server. So you can override anything in `issues/settings_local.py`.

## Configuration

In order to fetch issues from both `GitHub` and `ZenHub`, you need to specify your tokens.

* [Get your ZenHub token](https://dashboard.zenhub.io/#/settings)
* [Get your GitHub token](https://github.com/settings/tokens) (Select repo scope)

![repo](resources/github_scope.png)

create a file called `credentials.py` under `issues` directory:

```
# issues/credentials.py

GITHUB = {
    'token': '<your token>',
    'owner': '<Organization or user name>'
}
ZENHUB = {
    'token': '<your token>'
}
```

`settings.py` will try to read this file.

## Preparing the database

Create postgresql database:

```
createdb issue_tracker
```

Run migrations

```
./manage.py migrate
```


## Getting Issues from GitHub and ZenHub

It is currently a manual process

```
./manage.py fetch --initial
```

* **initial:** Run the command for the first time. This parameter let's us fetch previously closed issues. 
* **fix:** If `--initial` is specified, you do not need to give this parameter. It may ask you questions about pipeline name mappings. We can not track previous name changes, so you have to define them on the first run. Otherwise you can just give this parameter and add new name changes without running another `--initial` fetch.


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

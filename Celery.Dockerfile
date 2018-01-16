FROM python:3.6

RUN mkdir /code
WORKDIR /code
ADD requirements/base.txt /code/
RUN pip install -r base.txt
ADD . /code/

RUN python manage.py collectstatic -link --noinput
ENV DJANGO_SETTINGS_MODULE 'zenhub_charts.settings_env'
CMD ["celery", "-A", "zenhub_charts", "worker", "-B", "-l", "info"] 

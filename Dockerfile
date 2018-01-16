FROM python:3.6

RUN mkdir /code
WORKDIR /code
ADD requirements/base.txt /code/
RUN pip install -r base.txt
ADD . /code/

EXPOSE 8000
RUN python manage.py collectstatic -link --noinput
ENV DJANGO_SETTINGS_MODULE 'zenhub_charts.settings_env'
CMD ["python", "/code/manage.py", "runserver", "0.0.0.0:8000", "--insecure"] 

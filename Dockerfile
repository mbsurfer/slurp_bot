FROM python:3.9.2
RUN pip install pipenv
COPY Pipfile* /tmp
RUN cd /tmp && pipenv lock --keep-outdated --requirements > requirements.txt
RUN pip install -r /tmp/requirements.txt
COPY . /tmp/app
RUN pip install /tmp/app
RUN chmod a+x /tmp/app/run.sh
CMD ["./tmp/app/run.sh"]
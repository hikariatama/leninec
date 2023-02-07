FROM python:3.8.5-slim-buster
ENV GIT_PYTHON_REFRESH=quiet

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY ./requirements.txt /app/requirements.txt

RUN pip install \
    --no-warn-script-location \
    --no-cache-dir \
    --upgrade \
    --disable-pip-version-check \
    -r /app/requirements.txt

RUN rm -rf /tmp/*

COPY . /app

WORKDIR /app/server

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "2931"]
EXPOSE 2931

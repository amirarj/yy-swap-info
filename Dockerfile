FROM python:3.8-buster

COPY ./requirements.txt /app/requirements.txt
WORKDIR /app

RUN apt update && apt install -qy libmariadbclient-dev gcc
RUN pip install -r requirements.txt

COPY . /app
CMD ["python", "app.py"]

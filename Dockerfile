FROM python:3.10

WORKDIR /app

ADD . /app/

RUN pip3 install --prefer-binary -r requirements.txt

EXPOSE 5000

ENV FLASK_APP=main
ENV FLASK_ENV=development

CMD ["python", "main.py"]

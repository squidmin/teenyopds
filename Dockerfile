FROM python:3.10

RUN mkdir /app
WORKDIR /app
ADD . /app/

RUN chmod -R 777 /app/static
RUN pip3 install --prefer-binary -r requirements.txt

EXPOSE 5000

ENV FLASK_APP=main
ENV FLASK_ENV=development

CMD ["python", "main.py"]

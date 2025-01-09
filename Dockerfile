FROM python:3.10

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip
RUN pip3 install --prefer-binary -r requirements.txt

RUN pip install pytest

EXPOSE 5000

ENV FLASK_APP=main
ENV FLASK_ENV=development

CMD ["python", "main.py"]

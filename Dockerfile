FROM python:3.10
RUN mkdir /app
WORKDIR /app
ADD . /app/
RUN pip3 install --prefer-binary -r requirements.txt
EXPOSE 5000
ENV FLASK_APP=main
CMD ["python", "main.py"]

FROM python:3.8-alpine

RUN pip install readerwriterlock

WORKDIR /app

COPY order_service.py .

ENTRYPOINT ["python", "-u", "order_service.py"]

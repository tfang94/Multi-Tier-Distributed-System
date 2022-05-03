FROM python:3.8-alpine

RUN pip install readerwriterlock

WORKDIR /app

COPY catalog_service.py .

ENTRYPOINT ["python", "-u", "catalog_service.py"]

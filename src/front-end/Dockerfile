FROM python:3.8-alpine

WORKDIR /app

COPY frontend_service.py .

ENTRYPOINT ["python", "-u", "frontend_service.py", "-z 1"]

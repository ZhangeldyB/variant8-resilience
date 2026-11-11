FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY core.py metrics.py test_core.py ./
COPY local_stand/dep.py local_stand/loadgen.py ./

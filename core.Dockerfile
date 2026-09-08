FROM python:3.11-slim
WORKDIR /opt/one2lv
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python -m py_compile unified_os.py core_service.py
EXPOSE 3002
CMD ["python3", "core_service.py"]

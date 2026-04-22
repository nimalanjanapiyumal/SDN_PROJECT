FROM python:3.12-slim
WORKDIR /opt/app
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080 9108
CMD ["python", "-m", "uvicorn", "adaptive_cloud_platform.app:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8080"]

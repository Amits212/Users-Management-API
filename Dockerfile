FROM python:3.9-slim


WORKDIR /app


COPY requirements .
RUN pip install --no-cache-dir -r requirements


COPY . .


CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

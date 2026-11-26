FROM python:3.12-slim

WORKDIR /src

COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ shared/
COPY worker/ .

CMD ["python", "main.py"]

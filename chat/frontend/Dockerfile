FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api.py app.py app.tcss ./

ENV PYTHONUNBUFFERED=1
ENV TERM=xterm-256color

CMD ["python", "app.py"]

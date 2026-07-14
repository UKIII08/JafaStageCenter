FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
# Socket.IO w trybie threading + simple-websocket (eventlet jest porzucony
# i nowy gunicorn go nie obsługuje). 1 worker, dużo wątków.
CMD ["gunicorn", "-w", "1", "--threads", "100", "-b", "0.0.0.0:8000", "run:app"]

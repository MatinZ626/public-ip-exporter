FROM python:3.12-alpine

WORKDIR /app


RUN addgroup -S appgroup && \
    adduser -S appuser -G appgroup

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appgroup app.py .

USER appuser

EXPOSE 9105

CMD ["gunicorn", "--bind", "0.0.0.0:9105", "app:app"]

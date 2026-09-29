FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-production.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements-production.lock
RUN useradd --create-home --uid 10001 eventapp
COPY --chown=eventapp:eventapp . /app
RUN mkdir -p /app/staticfiles /var/lib/tedx/media && chown -R eventapp:eventapp /app/staticfiles /var/lib/tedx
USER eventapp
ENV PRIVATE_MEDIA_ROOT=/var/lib/tedx/media
EXPOSE 8000
CMD ["sh", "scripts/serve.sh"]

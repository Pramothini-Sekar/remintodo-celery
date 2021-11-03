web: gunicorn app:app
beat: celery -A app beat --loglevel=info
worker: celery -A app worker

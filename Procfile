web:    daphne stockAnalysis_server.asgi:application
worker: celery -A stockAnalysis_server worker --loglevel=info
beat:   celery -A stockAnalysis_server beat --loglevel=info

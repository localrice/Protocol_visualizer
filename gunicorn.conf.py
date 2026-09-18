"""Gunicorn production configuration for Protocol Dashboard."""

bind = "127.0.0.1:5000"
workers = 1
threads = 4
worker_class = "gthread"
timeout = 30
keepalive = 2

"""Production entry point.

Run with a real WSGI server instead of Flask's development server, e.g.:

    waitress-serve --host=127.0.0.1 --port=5000 wsgi:application
"""
from app import app as application

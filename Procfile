web: gunicorn --config gunicorn.conf.py wsgi:application
worker: bench worker --queue long,default,short
scheduler: bench schedule
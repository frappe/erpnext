from celery import Celery
from Goldfish.config import settings

app = Celery('Goldfish',
             broker=settings.redis_url,
             backend=settings.redis_url,
             include=['Goldfish.tasks'])

app.conf.update(
    result_expires=3600,
)

if __name__ == '__main__':
    app.start()
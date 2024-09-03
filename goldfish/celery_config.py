from celery import Celery
from goldfish.config import settings

app = Celery('goldfish',
             broker=settings.redis_url,
             backend=settings.redis_url,
             include=['goldfish.tasks'])

app.conf.update(
    result_expires=3600,
)

if __name__ == '__main__':
    app.start()
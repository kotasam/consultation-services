from celery import Celery
from worke_consultation_service.config import config as cfg
import os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "worke_consultation_service.settings")
app = Celery(cfg.get("celery", "CELERY_QUEUE"), broker=cfg.get("celery", "AMPQ_URL"))

if __name__ == "__main__":
    app.start()

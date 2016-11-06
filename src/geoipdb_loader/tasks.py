from celery import shared_task
from celery.utils.log import get_task_logger
from . import download


logger = get_task_logger(__name__)


@shared_task(ignore_result=True)
def update_geoipdb():
    download(logger=logger)

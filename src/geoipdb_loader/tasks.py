from celery import shared_task
from celery.utils.log import get_task_logger
from . import download


logger = get_task_logger(__name__)


@shared_task(ignore_result=True)
def update_geoipdb(skip_city=False, skip_country=False, skip_md5=False):
    download(
        skip_city=skip_city,
        skip_country=skip_country,
        skip_md5=skip_md5,
        logger=logger,
    )

import errno
import gzip
import hashlib
import logging
import os
import shutil
import tempfile

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.six.moves import urllib

MAXMIND_URL = "http://geolite.maxmind.com/download/geoip/database/"


def _match_md5(fp, md5_url):
    md5 = urllib.request.urlopen(md5_url).read()
    m = hashlib.md5()
    for line in fp:
        m.update(line)
    fp.seek(0)
    return m.hexdigest() == md5.decode()


def _atomic_write(fp, dst):
    tmpfile = tempfile.NamedTemporaryFile(delete=False, dir=os.path.dirname(dst))
    shutil.copyfileobj(fp, tmpfile.file)
    tmpfile.file.flush()
    os.fsync(tmpfile.file.fileno())
    tmpfile.file.close()
    try:
        os.rename(tmpfile.name, dst)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
        os.unlink(dst)
        os.rename(tmpfile.name, dst)


def _download_file(maxmind_filename, skip_md5=False, local_filename=None):
    _, filename = os.path.split(maxmind_filename)
    if not os.path.exists(settings.GEOIP_PATH):
        raise ImproperlyConfigured("GEOIP_PATH directory doesn't exist on filesystem.")
    downloaded_file = os.path.join(settings.GEOIP_PATH, filename)
    if local_filename:
        db_file = os.path.join(settings.GEOIP_PATH, local_filename)
    else:
        db_file = os.path.splitext(downloaded_file)[0]
    urllib.request.urlretrieve(
        urllib.parse.urljoin(MAXMIND_URL, maxmind_filename), downloaded_file
    )
    with gzip.open(downloaded_file, "rb") as outfile:
        if not skip_md5:
            md5_url = urllib.parse.urljoin(
                MAXMIND_URL, filename.split(".", 1)[0] + ".md5"
            )
            if not _match_md5(outfile, md5_url):
                try:
                    os.remove(downloaded_file)
                finally:
                    raise ValueError(
                        "md5 of %s doesn't match the signature." % downloaded_file
                    )
        _atomic_write(outfile, db_file)
    os.remove(downloaded_file)


def _get_logger():
    return logging.getLogger(__name__)


def download(skip_city=False, skip_country=False, skip_md5=False, logger=None):
    logger = logger or _get_logger()
    files = []
    if not hasattr(settings, "GEOIP_PATH"):
        raise ImproperlyConfigured("GEOIP_PATH must be configured in settings.")
    if not skip_city:
        city_file = {
            "maxmind_filename": "GeoLite2-City.mmdb.gz",
            "skip_md5": skip_md5,
            "local_filename": getattr(settings, "GEOIP_CITY", None),
        }
        files.append(city_file)
    if not skip_country:
        country_file = {
            "maxmind_filename": "GeoLite2-Country.mmdb.gz",
            "skip_md5": skip_md5,
            "local_filename": getattr(settings, "GEOIP_COUNTRY", None),
        }
        files.append(country_file)
    if not files:
        logger.warn("Nothing to download.")
        return
    for entry in files:
        logger.info("Downloading %s ..." % entry["maxmind_filename"])
        _download_file(**entry)
    logger.info("Geoip files are updated.")

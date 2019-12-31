import errno
import hashlib
import logging
import os
import shutil
import tarfile
import tempfile
import urllib.request

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

MAXMIND_URL = (
    "https://download.maxmind.com/app/geoip_download"
    "?edition_id={filename}&license_key={license_key}&suffix=tar.gz"
)


def _match_md5(filename, md5_url):
    md5 = urllib.request.urlopen(md5_url).read()
    m = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            m.update(chunk)
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


def _download_file(kind, skip_md5=False, local_filename=None):
    if not os.path.exists(settings.GEOIP_PATH):
        raise ImproperlyConfigured("GEOIP_PATH directory doesn't exist on filesystem.")
    filename = "GeoLite2-{kind}".format(kind=kind)
    downloaded_file = os.path.join(
        settings.GEOIP_PATH, "{filename}.tar.gz".format(filename=filename)
    )
    db_file = os.path.join(
        settings.GEOIP_PATH,
        local_filename
        if local_filename
        else "{filename}.mmdb".format(filename=filename),
    )
    file_url = MAXMIND_URL.format(
        filename=filename, license_key=settings.MAXMIND_LICENSE_KEY
    )
    urllib.request.urlretrieve(file_url, downloaded_file)
    if not skip_md5:
        if not _match_md5(downloaded_file, file_url + ".md5"):
            try:
                os.remove(downloaded_file)
            finally:
                raise ValueError(
                    "md5 of %s doesn't match the signature." % downloaded_file
                )
    with tarfile.open(downloaded_file, "r:gz") as tf:
        outfile = tf.extractfile(
            next(
                m
                for m in tf.getmembers()
                if m.name.endswith("{filename}.mmdb".format(filename=filename))
            )
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
    if not hasattr(settings, "MAXMIND_LICENSE_KEY"):
        raise ImproperlyConfigured("MAXMIND_LICENSE_KEY must be set in settings.")
    if not skip_city:
        city_file = {
            "kind": "City",
            "skip_md5": skip_md5,
            "local_filename": getattr(settings, "GEOIP_CITY", None),
        }
        files.append(city_file)
    if not skip_country:
        country_file = {
            "kind": "Country",
            "skip_md5": skip_md5,
            "local_filename": getattr(settings, "GEOIP_COUNTRY", None),
        }
        files.append(country_file)
    if not files:
        logger.warn("Nothing to download.")
        return
    for entry in files:
        logger.info("Downloading %s db ..." % entry["kind"])
        _download_file(**entry)
    logger.info("Geoip files are updated.")

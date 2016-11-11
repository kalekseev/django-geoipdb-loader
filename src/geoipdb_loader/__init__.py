from __future__ import print_function

import os
import shutil
import errno
import tempfile
import gzip
import hashlib
import logging
import django
from django.utils.six.moves import urllib
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings


MAXMIND_URL = 'http://geolite.maxmind.com/download/geoip/database/'


def _match_md5(fp, md5_url):
    md5 = urllib.request.urlopen(md5_url).read()
    m = hashlib.md5()
    for line in fp:
        m.update(line)
    fp.seek(0)
    return m.hexdigest() == md5


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


def _get_geoipdb_version():
    geoipdb_version = getattr(settings, 'GEOIPDB_VERSION', None)
    if geoipdb_version in (1, 2):
        return geoipdb_version
    if django.VERSION[:2] == (1, 8):
        return 1
    return 2


def _download_file(filepath, skip_md5=False):
    _, filename = os.path.split(filepath)
    downloaded_file = os.path.join(settings.GEOIP_PATH, filename)
    db_file = os.path.splitext(downloaded_file)[0]
    urllib.request.urlretrieve(
        urllib.parse.urljoin(MAXMIND_URL, filepath),
        downloaded_file
    )
    with gzip.open(downloaded_file, 'rb') as outfile:
        if not skip_md5:
            md5_url = urllib.parse.urljoin(
                MAXMIND_URL,
                filename.split('.', 1)[0] + '.md5'
            )
            if not _match_md5(outfile, md5_url):
                try:
                    os.remove(downloaded_file)
                finally:
                    raise ValueError(
                        'md5 of %s doesn\'t match the signature.' % downloaded_file
                    )
        _atomic_write(outfile, db_file)
    os.remove(downloaded_file)


def download(skip_city=False, skip_country=False, skip_md5=False, logger=None):
    if not logger:
        logger = logging.getLogger(__name__)
    geoipdb_version = _get_geoipdb_version()
    files = []
    if not hasattr(settings, 'GEOIP_PATH'):
        raise ImproperlyConfigured('GEOIP_PATH must be configured in settings.')
    if not skip_city:
        files.append(
            'GeoLite2-City.mmdb.gz' if geoipdb_version == 2 else 'GeoLiteCity.dat.gz',
        )
    if not skip_country:
        files.append(
            'GeoLite2-Country.mmdb.gz' if geoipdb_version == 2 else 'GeoLiteCountry/GeoIP.dat.gz',
        )
    if not files:
        logger.warn('Nothing to download.')
        return
    for filename in files:
        logger.info('Downloading %s ...' % filename)
        _download_file(filename, skip_md5=skip_md5)
    logger.info('Geoip files are updated.')

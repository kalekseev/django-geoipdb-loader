import errno
import gzip
import hashlib
import logging
import os
import shutil
import tempfile

import django
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.six.moves import urllib


MAXMIND_URL = 'http://geolite.maxmind.com/download/geoip/database/'


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


def _get_geoipdb_version():
    geoipdb_version = getattr(settings, 'GEOIPDB_VERSION', None)
    if geoipdb_version in (1, 2):
        return geoipdb_version
    if django.VERSION[:2] == (1, 8):
        return 1
    return 2


def _download_file(maxmind_filename, skip_md5=False, local_filename=None):
    _, filename = os.path.split(maxmind_filename)
    downloaded_file = os.path.join(settings.GEOIP_PATH, filename)
    if local_filename:
        db_file = os.path.join(settings.GEOIP_PATH, local_filename)
    else:
        db_file = os.path.splitext(downloaded_file)[0]
    urllib.request.urlretrieve(
        urllib.parse.urljoin(MAXMIND_URL, maxmind_filename),
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
        city_file = {
            'maxmind_filename': 'GeoLite2-City.mmdb.gz',
            'skip_md5': skip_md5,
            'local_filename': getattr(settings, 'GEOIP_CITY', None),
        }
        if geoipdb_version == 1:
            city_file['maxmind_filename'] = 'GeoLiteCity.dat.gz'
            city_file['skip_md5'] = True
        files.append(city_file)
    if not skip_country:
        country_file = {
            'maxmind_filename': 'GeoLite2-Country.mmdb.gz',
            'skip_md5': skip_md5,
            'local_filename': getattr(settings, 'GEOIP_COUNTRY', None),
        }
        if geoipdb_version == 1:
            country_file['maxmind_filename'] = 'GeoLiteCountry/GeoIP.dat.gz'
            country_file['skip_md5'] = True
        files.append(country_file)
    if not files:
        logger.warn('Nothing to download.')
        return
    for entry in files:
        logger.info('Downloading %s ...' % entry['maxmind_filename'])
        _download_file(**entry)
    logger.info('Geoip files are updated.')

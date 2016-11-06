from __future__ import print_function

import os
import gzip
import hashlib
import logging
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


def _download_file(filename, skip_md5=False):
    downloaded_file = os.path.join(settings.GEOIP_PATH, filename)
    db_file = os.path.splitext(downloaded_file)[0]
    urllib.request.urlretrieve(
        urllib.parse.urljoin(MAXMIND_URL, filename),
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
        with open(db_file, 'wb') as infile:
            infile.writelines(outfile)
    os.remove(downloaded_file)


def download(skip_city=False, skip_country=False, skip_md5=False, logger=None):
    if not logger:
        logger = logging.getLogger(__name__)
    files = []
    if not hasattr(settings, 'GEOIP_PATH'):
        raise ImproperlyConfigured('GEOIP_PATH must be configured in settings.')
    if not skip_city:
        files.append('GeoLite2-City.mmdb.gz')
    if not skip_country:
        files.append('GeoLite2-Country.mmdb.gz')
    if not files:
        logger.warn('Nothing to download.')
        return
    for filename in files:
        logger.info('Downloading %s ...' % filename)
        _download_file(filename, skip_md5=skip_md5)
    logger.info('Geoip files are updated.')

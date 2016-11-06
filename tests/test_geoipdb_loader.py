import gzip
import hashlib
import random
import string
import sys
from io import BytesIO
import geoipdb_loader

import pytest
from django.utils import six

PY2 = sys.version_info[0] == 2


if PY2:
    import mock
else:
    from unittest import mock


@pytest.fixture
def random_string():
    return bytes(b''.join(
        six.b(random.choice(string.ascii_uppercase + string.digits + '\n'))
        for _ in range(100)
    ))


def test_match_md5(monkeypatch, settings, random_string):
    md5 = hashlib.md5()
    md5.update(random_string)
    md5sum = md5.hexdigest()
    urlopen_mock = mock.Mock(return_value=mock.Mock(read=lambda: md5sum))
    monkeypatch.setattr('django.utils.six.moves.urllib.request.urlopen', urlopen_mock)
    fp = BytesIO(random_string)
    assert geoipdb_loader._match_md5(fp, 'someurl')
    urlopen_mock.assert_called_once_with('someurl')
    assert fp.read() == random_string


@pytest.mark.parametrize('is_md5_match', [False, True])
@pytest.mark.parametrize('skip_md5', [False, True])
def test_download_file(monkeypatch, tmpdir, settings, random_string, is_md5_match, skip_md5):
    def create_gzip(url, filename):
        with gzip.open(filename, 'wb') as f:
            f.write(random_string)

    settings.GEOIP_PATH = str(tmpdir)
    monkeypatch.setattr(
        'django.utils.six.moves.urllib.request.urlretrieve',
        mock.Mock(side_effect=create_gzip)
    )
    match_md5_mock = mock.Mock(return_value=is_md5_match)
    monkeypatch.setattr('geoipdb_loader._match_md5', match_md5_mock)
    if is_md5_match or skip_md5:
        geoipdb_loader._download_file('somedb.mmdb.gz', skip_md5=skip_md5)
        assert open(str(tmpdir.join('somedb.mmdb')), 'rb').read() == random_string
    else:
        with pytest.raises(ValueError) as e:
            geoipdb_loader._download_file('somedb.mmdb.gz', skip_md5=skip_md5)
        assert str(e.value) == 'md5 of %s doesn\'t match the signature.' % tmpdir.join('somedb.mmdb.gz')
    if not skip_md5:
        assert match_md5_mock.call_count == 1

import gzip
import hashlib
import random
import string
import sys
from io import BytesIO

import geoipdb_loader
import pytest
from django.core import management
from django.core.exceptions import ImproperlyConfigured
from django.utils import six

PY2 = sys.version_info[0] == 2


if PY2:
    import mock
else:
    from unittest import mock


@pytest.fixture
def random_bytes():
    return six.b(
        "".join(
            random.choice(string.ascii_uppercase + string.digits + "\n")
            for _ in range(100)
        )
    )


def test_match_md5(monkeypatch, random_bytes):
    md5 = hashlib.md5()
    md5.update(random_bytes)
    md5sum = md5.hexdigest()
    urlopen_mock = mock.Mock(return_value=mock.Mock(read=lambda: six.b(md5sum)))
    monkeypatch.setattr("django.utils.six.moves.urllib.request.urlopen", urlopen_mock)
    fp = BytesIO(random_bytes)
    assert geoipdb_loader._match_md5(fp, "someurl")
    urlopen_mock.assert_called_once_with("someurl")
    assert fp.read() == random_bytes


@pytest.mark.parametrize("is_md5_match", [False, True])
@pytest.mark.parametrize("skip_md5", [False, True])
def test_download_file(
    monkeypatch, tmpdir, settings, random_bytes, is_md5_match, skip_md5
):
    def create_gzip(url, filename):
        with gzip.open(filename, "wb") as f:
            f.write(random_bytes)

    settings.GEOIP_PATH = str(tmpdir)
    monkeypatch.setattr(
        "django.utils.six.moves.urllib.request.urlretrieve",
        mock.Mock(side_effect=create_gzip),
    )
    match_md5_mock = mock.Mock(return_value=is_md5_match)
    monkeypatch.setattr("geoipdb_loader._match_md5", match_md5_mock)
    if is_md5_match or skip_md5:
        geoipdb_loader._download_file("somedb.mmdb.gz", skip_md5=skip_md5)
        assert open(str(tmpdir.join("somedb.mmdb")), "rb").read() == random_bytes
    else:
        with pytest.raises(ValueError) as e:
            geoipdb_loader._download_file("somedb.mmdb.gz", skip_md5=skip_md5)
        assert str(e.value) == "md5 of %s doesn't match the signature." % tmpdir.join(
            "somedb.mmdb.gz"
        )
    if skip_md5:
        assert not match_md5_mock.call_count
    else:
        assert match_md5_mock.call_count == 1


@pytest.mark.parametrize("skip_city", [False, True])
@pytest.mark.parametrize("skip_country", [False, True])
@pytest.mark.parametrize("skip_md5", [False, True])
def test_command(monkeypatch, settings, tmpdir, skip_city, skip_country, skip_md5):
    settings.GEOIP_PATH = str(tmpdir)
    download_file_mock = mock.Mock()
    monkeypatch.setattr("geoipdb_loader._download_file", download_file_mock)
    out = six.StringIO()
    args = []
    if skip_city:
        args.append("--skip-city")
    if skip_country:
        args.append("--skip-country")
    if skip_md5:
        args.append("--skip-md5")
    management.call_command("download_geoipdb", stdout=out, *args)
    if not skip_city:
        download_file_mock.assert_any_call(
            maxmind_filename="GeoLite2-City.mmdb.gz",
            skip_md5=skip_md5,
            local_filename=None,
        )
    if not skip_country:
        download_file_mock.assert_any_call(
            maxmind_filename="GeoLite2-Country.mmdb.gz",
            skip_md5=skip_md5,
            local_filename=None,
        )
    assert download_file_mock.call_count == int(not skip_city) + int(not skip_country)


def test_download_edge_cases(monkeypatch, settings, tmpdir):
    with pytest.raises(ImproperlyConfigured) as e:
        geoipdb_loader.download(skip_city=True, skip_country=True)
    assert str(e.value) == "GEOIP_PATH must be configured in settings."
    log_mock = mock.Mock()
    settings.GEOIP_PATH = str(tmpdir)
    monkeypatch.setattr("geoipdb_loader._get_logger", lambda: log_mock)
    geoipdb_loader.download(skip_city=True, skip_country=True)
    log_mock.warn.assert_called_once_with("Nothing to download.")


@pytest.mark.parametrize("paths", [(None, None), ("country.dat", "city.mmdb")])
def test_geoipdb_version(monkeypatch, settings, tmpdir, random_bytes, paths):
    def create_gzip(url, filename):
        suffix = "city" if "city" in filename.lower() else "country"
        with gzip.open(filename, "wb") as f:
            f.write(random_bytes + six.b(suffix))

    settings.GEOIP_COUNTRY, settings.GEOIP_CITY = paths
    settings.GEOIP_PATH = str(tmpdir)
    monkeypatch.setattr(
        "django.utils.six.moves.urllib.request.urlretrieve",
        mock.Mock(side_effect=create_gzip),
    )
    geoipdb_loader.download(skip_md5=True)

    assert open(
        str(tmpdir.join(settings.GEOIP_COUNTRY or "GeoLite2-Country.mmdb")), "rb"
    ).read() == random_bytes + six.b("country")
    assert open(
        str(tmpdir.join(settings.GEOIP_CITY or "GeoLite2-City.mmdb")), "rb"
    ).read() == random_bytes + six.b("city")


def test_download_on_version(monkeypatch, settings, tmpdir):
    settings.GEOIP_PATH = str(tmpdir)
    download_file_mock = mock.Mock()
    monkeypatch.setattr("geoipdb_loader._download_file", download_file_mock)
    geoipdb_loader.download()
    download_file_mock.assert_any_call(
        maxmind_filename="GeoLite2-City.mmdb.gz", skip_md5=False, local_filename=None
    )
    download_file_mock.assert_any_call(
        maxmind_filename="GeoLite2-Country.mmdb.gz", skip_md5=False, local_filename=None
    )
    assert download_file_mock.call_count == 2

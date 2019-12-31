import hashlib
import os
import random
import string
import sys
import tarfile
from io import StringIO

import geoipdb_loader
import pytest
from django.core import management
from django.core.exceptions import ImproperlyConfigured

PY2 = sys.version_info[0] == 2


if PY2:
    import mock
else:
    from unittest import mock


def random_str(size=20):
    return "".join(
        random.choice(string.ascii_uppercase + string.digits + "\n") for _ in range(100)
    )


@pytest.fixture
def random_bytes():
    return random_str(100).encode("utf8")


@pytest.fixture
def create_tar(tmpdir, random_bytes):
    def _create_tar(url, filename):
        suffix = "city" if "city" in filename.lower() else "country"
        directory = os.path.join(str(tmpdir), random_str())
        os.mkdir(directory)
        fpath = os.path.join(
            directory, "GeoLite2-{kind}.mmdb".format(kind=suffix.title())
        )
        with open(fpath, "wb") as f:
            f.write(random_bytes + suffix.encode("utf8"))
        with tarfile.open(filename, "w:gz") as f:
            f.add(directory)

    return _create_tar


def test_match_md5(monkeypatch, random_bytes, tmpdir):
    md5 = hashlib.md5()
    md5.update(random_bytes)
    md5sum = md5.hexdigest()
    urlopen_mock = mock.Mock(return_value=mock.Mock(read=lambda: md5sum.encode("utf8")))
    monkeypatch.setattr("urllib.request.urlopen", urlopen_mock)
    filename = os.path.join(str(tmpdir), "md5")
    with open(filename, "wb") as f:
        f.write(random_bytes)
    assert geoipdb_loader._match_md5(filename, "someurl")
    urlopen_mock.assert_called_once_with("someurl")


@pytest.mark.parametrize("is_md5_match", [False, True])
@pytest.mark.parametrize("skip_md5", [False, True])
def test_download_file(
    monkeypatch, tmpdir, settings, is_md5_match, skip_md5, create_tar, random_bytes
):
    settings.GEOIP_PATH = str(tmpdir)
    settings.MAXMIND_LICENSE_KEY = "randomstringkey"
    monkeypatch.setattr("urllib.request.urlretrieve", mock.Mock(side_effect=create_tar))
    match_md5_mock = mock.Mock(return_value=is_md5_match)
    monkeypatch.setattr("geoipdb_loader._match_md5", match_md5_mock)
    if is_md5_match or skip_md5:
        geoipdb_loader._download_file("City", skip_md5=skip_md5)
        assert (
            open(str(tmpdir.join("GeoLite2-City.mmdb")), "rb").read()
            == random_bytes + b"city"
        )
    else:
        with pytest.raises(ValueError) as e:
            geoipdb_loader._download_file("City", skip_md5=skip_md5)
        assert str(e.value) == "md5 of %s doesn't match the signature." % tmpdir.join(
            "GeoLite2-City.tar.gz"
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
    settings.MAXMIND_LICENSE_KEY = "randomstringkey"
    download_file_mock = mock.Mock()
    monkeypatch.setattr("geoipdb_loader._download_file", download_file_mock)
    out = StringIO()
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
            kind="City", skip_md5=skip_md5, local_filename=None
        )
    if not skip_country:
        download_file_mock.assert_any_call(
            kind="Country", skip_md5=skip_md5, local_filename=None
        )
    assert download_file_mock.call_count == int(not skip_city) + int(not skip_country)


def test_download_edge_cases(monkeypatch, settings, tmpdir):
    with pytest.raises(ImproperlyConfigured) as e:
        geoipdb_loader.download(skip_city=True, skip_country=True)
    assert str(e.value) == "GEOIP_PATH must be configured in settings."
    log_mock = mock.Mock()
    settings.GEOIP_PATH = str(tmpdir)
    settings.MAXMIND_LICENSE_KEY = "randomstringkey"
    monkeypatch.setattr("geoipdb_loader._get_logger", lambda: log_mock)
    geoipdb_loader.download(skip_city=True, skip_country=True)
    log_mock.warn.assert_called_once_with("Nothing to download.")


@pytest.mark.parametrize("paths", [(None, None), ("country.dat", "city.mmdb")])
def test_geoipdb_version(
    monkeypatch, settings, tmpdir, random_bytes, paths, create_tar
):
    settings.GEOIP_COUNTRY, settings.GEOIP_CITY = paths
    settings.GEOIP_PATH = str(tmpdir)
    settings.MAXMIND_LICENSE_KEY = "randomstringkey"
    monkeypatch.setattr("urllib.request.urlretrieve", mock.Mock(side_effect=create_tar))
    geoipdb_loader.download(skip_md5=True)

    assert (
        open(
            str(tmpdir.join(settings.GEOIP_COUNTRY or "GeoLite2-Country.mmdb")), "rb"
        ).read()
        == random_bytes + b"country"
    )
    assert (
        open(str(tmpdir.join(settings.GEOIP_CITY or "GeoLite2-City.mmdb")), "rb").read()
        == random_bytes + b"city"
    )


def test_download_on_version(monkeypatch, settings, tmpdir):
    settings.GEOIP_PATH = str(tmpdir)
    settings.MAXMIND_LICENSE_KEY = "randomstringkey"
    download_file_mock = mock.Mock()
    monkeypatch.setattr("geoipdb_loader._download_file", download_file_mock)
    geoipdb_loader.download()
    download_file_mock.assert_any_call(kind="City", skip_md5=False, local_filename=None)
    download_file_mock.assert_any_call(
        kind="Country", skip_md5=False, local_filename=None
    )
    assert download_file_mock.call_count == 2

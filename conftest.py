from django.conf import settings


def pytest_configure():
    settings.configure(
        INSTALLED_APPS=['geoipdb_loader'],
        GEOIPDB_VERSION=2,
    )

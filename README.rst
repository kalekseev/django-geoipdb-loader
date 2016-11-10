======================
Django GeoIP DB Loader
======================

.. start-badges

.. list-table::
    :stub-columns: 1

    * - tests
      - |travis|

.. |travis| image:: https://travis-ci.org/kalekseev/django-geoipdb-loader.svg?branch=master
    :alt: Travis-Ci Build Status
    :target: https://travis-ci.org/kalekseev/django-geoipdb-loader


.. end-badges

Helps download and keep updated maxmind's geoip db required for django GeoIP2 (django 1.9+)


Why and when to use?
====================

If you don't mind installing and configuring official geoipupdate binary on your server
then I'd recommend to use it http://dev.maxmind.com/geoip/geoipupdate/
This app was designed for quick and easy setup of geoipdb via django settings.


Installation
============

Using pip::

    pip install django-geoipdb-loader

Add the app to INSTALLED_APPS in settings file and configure GEOIP_PATH::

    INSTALLED_APPS = [
        ...
        geoipdb_loader,
        ...
    ]

    GEOIP_PATH = '/myproject/geoip'

Run `manage.py download_geoipdb` to download geoip files


In order to automatically update the geoip files you can use provided celery task::

    CELERYBEAT_SCHEDULE = {
        'update-geoipdb': {
            'task': 'geoipdb_loader.tasks.update_geoipdb',
            'schedule': crontab(day_of_week=7),
        },
    }

or crontab::

    * * * * 7 manage.py download_geoipdb

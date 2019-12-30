======================
Django GeoIP DB Loader
======================

.. start-badges

.. list-table::
    :stub-columns: 1

    * - tests
      - | |travis| |coveralls|

.. |travis| image:: https://travis-ci.org/kalekseev/django-geoipdb-loader.svg?branch=master
    :alt: Travis-Ci Build Status
    :target: https://travis-ci.org/kalekseev/django-geoipdb-loader

.. |coveralls| image:: https://coveralls.io/repos/github/kalekseev/django-geoipdb-loader/badge.svg?branch=master
    :alt: Coverage Status
    :target: https://coveralls.io/repos/github/kalekseev/django-geoipdb-loader


.. end-badges

Helps download and keep updated maxmind's geoip db required for `django GeoIP <https://docs.djangoproject.com/en/1.10/ref/contrib/gis/geoip2/>`_

Django versions 1.11+ are supported.


Why and when to use?
====================

If you don't mind installing and configuring
`official geoipupdate <http://dev.maxmind.com/geoip/geoipupdate/>`_ on your server
then I'd recommend to use it.
If you want a simple method to download db files via django command or schedule
updates using celery then this app is the way to go.


Installation
============

Using pip::

    pip install django-geoipdb-loader

Add the app to INSTALLED_APPS and configure GEOIP_PATH::

    INSTALLED_APPS = [
        ...
        geoipdb_loader,
        ...
    ]

    GEOIP_PATH = '/myproject/geoip'
    MAXMIND_LICENSE_KEY = 'your license key'


Usage
=====

Run :code:`manage.py download_geoipdb` to download geoip files.

In order to automatically update the geoip files you can use provided celery task::

    CELERYBEAT_SCHEDULE = {
        'update-geoipdb': {
            'task': 'geoipdb_loader.tasks.update_geoipdb',
            'schedule': crontab(day_of_week=6),
        },
    }

or crontab::

    * * * * 6 manage.py download_geoipdb

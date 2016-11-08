from django.core.management.base import BaseCommand
from ... import download


class Logger(object):
    def __init__(self, style, stdout):
        self.style = style
        self.stdout = stdout

    def warn(self, template, *args):
        self.stdout.write(self.style.WARNING(template % args))

    def info(self, template, *args):
        self.stdout.write(template % args)


class Command(BaseCommand):
    help = "Download or update maxmind geoip db"

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-city',
            action='store_true',
            dest='skip_city',
            help='Don\'t download city db'
        )
        parser.add_argument(
            '--skip-country',
            action='store_true',
            dest='skip_country',
            help='Don\'t download country db'
        )
        parser.add_argument(
            '--skip-md5',
            action='store_true',
            dest='skip_md5',
            help='Don\'t check md5 sum of the downloaded files'
        )

    def handle(self, *args, **options):
        download(
            skip_city=options['skip_city'],
            skip_country=options['skip_country'],
            skip_md5=options['skip_md5'],
            logger=Logger(self.style, self.stdout),
        )

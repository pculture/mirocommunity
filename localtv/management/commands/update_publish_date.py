from django.core.management.base import NoArgsCommand

import vidscraper

from localtv.management import site_too_old
from localtv import models

class Command(NoArgsCommand):

    args = ''

    def handle_noargs(self, **options):
        if site_too_old():
            return
        for v in models.Video.objects.filter(when_published__isnull=True):
            try:
                d = vidscraper.auto_scrape(v.website_url, fields=[
                        'publish_date'])
            except:
                pass
            else:
                if d:
                    v.when_published = d['publish_date']
                    v.save()

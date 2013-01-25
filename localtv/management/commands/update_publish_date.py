from django.core.management.base import NoArgsCommand

import vidscraper

from localtv.management import site_too_old
from localtv.settings import API_KEYS
from localtv import models

class Command(NoArgsCommand):

    args = ''

    def handle_noargs(self, **options):
        if site_too_old():
            return
        for v in models.Video.objects.filter(when_published__isnull=True):
            try:
                video = vidscraper.auto_scrape(v.website_url, fields=[
                        'publish_datetime'], api_keys=API_KEYS)
            except:
                pass
            else:
                if video:
                    v.when_published = video.publish_datetime
                    v.save()

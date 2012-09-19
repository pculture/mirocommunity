import datetime
import logging

from django.core.management.base import NoArgsCommand
from localtv.management import site_too_old
from localtv import models

class Command(NoArgsCommand):

    args = ''

    def handle_noargs(self, **options):
        if site_too_old():
            return
        newsletter = models.NewsletterSettings.objects.get_current()
        if not newsletter.repeat:
            return
        if not newsletter.site_settings.get_tier().permit_newsletter():
            return

        now = datetime.datetime.now()
        if now > newsletter.next_send_time():
            logging.warning('Sending newsletter for %s',
                            newsletter.site_settings.site.domain)
            newsletter.send()
            # we increment by the repeat so that last_sent maintains the
            # weekday and hour that the user has assigned
            repeat = datetime.timedelta(hours=newsletter.repeat)
            while newsletter.next_send_time() < now:
                newsletter.last_sent += repeat
            newsletter.save()
            logging.warning('Next send scheduled for %s',
                            newsletter.next_send_time())

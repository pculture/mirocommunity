import datetime

from django.core.management.base import NoArgsCommand
from django.template import Context, loader

from localtv.models import Video, SiteSettings
from localtv import utils

class Command(NoArgsCommand):

    def handle_noargs(self, **kwargs):
        self.send_email(datetime.timedelta(hours=24),
                        'today',
                        'admin_queue_daily')
        if datetime.date.today().weekday == 0: # Monday
            self.send_email(
                datetime.timedelta(days=7),
                'last week',
                'admin_queue_weekly')

    def send_email(self, delta, time_period, notice_type):
        site_settings = SiteSettings.objects.get_current()

        previous = datetime.datetime.now() - delta

        queue_videos = Video.objects.filter(
            status=Video.NEEDS_MODERATION,
            site=site_settings.site,
        )
        new_videos = queue_videos.filter(when_submitted__gte=previous)

        if new_videos.count():
            subject = 'Video Submissions for %s' % site_settings.site.name
            t = loader.get_template(
                'localtv/submit_video/review_status_email.txt')
            c = Context({'new_videos': new_videos,
                         'queue_videos': queue_videos,
                         'time_period': time_period,
                         'site': site_settings.site})
            message = t.render(c)
            utils.send_notice(notice_type,
                             subject, message,
                             site_settings=site_settings)

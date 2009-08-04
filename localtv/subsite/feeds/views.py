import datetime

from django.contrib.syndication.feeds import Feed
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.utils.translation import ugettext as _

from localtv import models
from localtv.decorators import get_sitelocation


FLASH_ENCLOSURE_STATIC_LENGTH = 1

LOCALTV_FEED_LENGTH = 30

class BaseVideosFeed(Feed):
    title_template = "localtv/subsite/feed/title.html"
    description_template = "localtv/subsite/feed/description.html"

    def __init__(self, *args, **kwargs):
        Feed.__init__(self, *args, **kwargs)
        self.sitelocation = models.SiteLocation.objects.get(
            site=models.Site.objects.get_current())

    def item_pubdate(self, video):
        return video.when_approved

    def item_link(self, video):
        return reverse('localtv_view_video', kwargs={'video_id': video.id})

    def item_enclosure_url(self, video):
        if video.file_url:
            return video.file_url
        elif video.flash_enclosure_url:
            return video.flash_enclosure_url

    def item_enclosure_length(self, video):
        if video.file_url:
            return video.file_url_length
        elif video.flash_enclosure_url:
            return FLASH_ENCLOSURE_STATIC_LENGTH

    def item_enclosure_mime_type(self, video):
        if video.file_url:
            return video.file_url_mimetype
        else:
            return 'application/x-shockwave-flash'


class NewVideosFeed(BaseVideosFeed):
    def link(self):
        return reverse('localtv_subsite_list_new')

    def title(self):
        return "%s: %s" % (
            self.sitelocation.site.name, _('New Videos'))

    def items(self):
        videos = models.Video.objects.filter(
            site=self.sitelocation.site,
            status=models.VIDEO_STATUS_ACTIVE)
        videos = videos.order_by(
            '-when_approved', '-when_submitted')
        return videos[:LOCALTV_FEED_LENGTH]

            
def new(request):
    feed = NewVideosFeed(None, request).get_feed(None)
    return HttpResponse(feed.writeString('utf8'))

        
class FeaturedVideosFeed(BaseVideosFeed):
    def link(self):
        return reverse('localtv_subsite_list_featured')

    def title(self):
        return "%s: %s" % (
            self.sitelocation.site.name, _('Featured Videos'))

    def items(self):
        videos = models.Video.objects.filter(
            site=self.sitelocation.site,
            last_featured__isnull=False,
            status=models.VIDEO_STATUS_ACTIVE)
        videos = videos.order_by(
            '-last_featured', '-when_approved','-when_submitted')
        return videos[:LOCALTV_FEED_LENGTH]


def featured(request):
    feed = FeaturedVideosFeed(None, request).get_feed(None)
    return HttpResponse(feed.writeString('utf8'))

        
class PopularVideosFeed(BaseVideosFeed):
    def link(self):
        return reverse('localtv_subsite_list_popular')

    def items(self):
        videos = models.Video.popular_since(
            datetime.timedelta(days=1), self.sitelocation,
            status=models.VIDEO_STATUS_ACTIVE)
        return videos[:LOCALTV_FEED_LENGTH]

    def title(self):
        return "%s: %s" % (
            self.sitelocation.site.name, _('Popular Videos'))


def popular(request):
    feed = PopularVideosFeed(None, request).get_feed(None)
    return HttpResponse(feed.writeString('utf8'))

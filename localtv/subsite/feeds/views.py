# Copyright 2009 - Participatory Culture Foundation
# 
# This file is part of Miro Community.
# 
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
# 
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.

import datetime

from django.contrib.syndication.feeds import Feed, FeedDoesNotExist
from django.core.files.storage import default_storage
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.utils import feedgenerator
from django.utils.translation import ugettext as _

from localtv import models

FLASH_ENCLOSURE_STATIC_LENGTH = 1

LOCALTV_FEED_LENGTH = 30

class ThumbnailFeedGenerator(feedgenerator.Atom1Feed):

    def root_attributes(self):
        attrs = feedgenerator.Atom1Feed.root_attributes(self)
        attrs['xmlns:media'] = 'http://search.yahoo.com/mrss/'
        return attrs

    def add_item_elements(self, handler, item):
        feedgenerator.Atom1Feed.add_item_elements(self, handler, item)
        if 'thumbnail' in item:
            handler.addQuickElement('icon', item['thumbnail'])
        if 'website_url' in item:
            handler.addQuickElement('link', attrs={
                    'rel': 'via',
                    'href': item['website_url']})
        if 'embed_code' in item:
            handler.startElement('media:player',
                                 {'url': item.get('website_url', '')})
            handler.characters(item['embed_code'])
            handler.endElement('media:player')


class BaseVideosFeed(Feed):
    title_template = "localtv/subsite/feed/title.html"
    description_template = "localtv/subsite/feed/description.html"
    feed_type = ThumbnailFeedGenerator

    def __init__(self, *args, **kwargs):
        Feed.__init__(self, *args, **kwargs)
        self.sitelocation = models.SiteLocation.objects.get(
            site=models.Site.objects.get_current())

    def item_pubdate(self, video):
        return video.when_published or video.when_approved

    def item_link(self, video):
        return video.get_absolute_url()

    def item_extra_kwargs(self, item):
        kwargs = {}
        if item.website_url:
            kwargs['website_url'] = item.website_url
        if item.has_thumbnail:
            if item.thumbnail_url:
                kwargs['thumbnail'] = item.thumbnail_url
            else:
                kwargs['thumbnail'] = 'http://%s%s' % (
                    self.sitelocation.site.domain,
                    default_storage.url(
                        item.get_resized_thumb_storage_path(375, 295)))
        if item.embed_code:
            kwargs['embed_code'] = item.embed_code
        return kwargs

    def item_enclosure_url(self, video):
        if video.file_url:
            return video.file_url
        elif video.flash_enclosure_url:
            return video.flash_enclosure_url

    def item_enclosure_length(self, video):
        if video.file_url_length:
            return video.file_url_length
        else:
            return FLASH_ENCLOSURE_STATIC_LENGTH

    def item_enclosure_mime_type(self, video):
        if video.file_url_mimetype:
            return video.file_url_mimetype
        elif video.flash_enclosure_url:
            return 'application/x-shockwave-flash'
        else:
            return ""


class NewVideosFeed(BaseVideosFeed):
    def link(self):
        return reverse('localtv_subsite_list_new')

    def title(self):
        return "%s: %s" % (
            self.sitelocation.site.name, _('New Videos'))

    def items(self):
        videos = models.Video.objects.new(
            site=self.sitelocation.site,
            status=models.VIDEO_STATUS_ACTIVE)
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
        videos = models.Video.objects.popular_since(
            datetime.timedelta(days=7), self.sitelocation,
            status=models.VIDEO_STATUS_ACTIVE)
        return videos[:LOCALTV_FEED_LENGTH]

    def title(self):
        return "%s: %s" % (
            self.sitelocation.site.name, _('Popular Videos'))


def popular(request):
    feed = PopularVideosFeed(None, request).get_feed(None)
    return HttpResponse(feed.writeString('utf8'))

class CategoryVideosFeed(BaseVideosFeed):
    def get_object(self, bits):
        return models.Category.objects.get(site=self.sitelocation.site,
                                           slug=bits[0])

    def link(self, category):
        return category.get_absolute_url()

    def items(self, category):
        videos = category.video_set.filter(
            status=models.VIDEO_STATUS_ACTIVE)
        return videos[:LOCALTV_FEED_LENGTH]

    def title(self, category):
        return "%s: %s" % (
            self.sitelocation.site.name, _('Category: %s') % category.name)


def category(request, category):
    try:
        feed = CategoryVideosFeed(None, request).get_feed(category)
    except FeedDoesNotExist:
        raise Http404
    return HttpResponse(feed.writeString('utf8'))


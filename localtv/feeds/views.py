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
import urllib

from django.contrib.auth.models import User
from django.contrib.syndication.feeds import Feed, FeedDoesNotExist, add_domain
from django.core import cache
from django.core.files.storage import default_storage
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.utils import feedgenerator
from django.utils.cache import patch_vary_headers
from django.utils.encoding import iri_to_uri
from django.utils.translation import ugettext as _
from django.utils.tzinfo import FixedOffset

from tagging.models import Tag
import simplejson

from localtv import models
from localtv.playlists.models import Playlist
from localtv.search.forms import VideoSearchForm
from localtv.templatetags.filters import simpletimesince

FLASH_ENCLOSURE_STATIC_LENGTH = 1

LOCALTV_FEED_LENGTH = 30

def feed_view(klass):
    def wrapper(request, *args):
        sitelocation = models.SiteLocation.objects.get_current()
        if len(args) == 0:
            args = [None]
        if args[0] == 'json/': # JSON feed
            json = True
        else:
            json = False
        args = args[1:]
        cache_key = ('feed_cache:%s:%s:%i:%s:%s' % (
            sitelocation.site.domain, klass.__name__, json, args,
            repr(request.GET.items()))).replace(' ', '')
        mime_type_and_output = cache.cache.get(cache_key)
        if mime_type_and_output is None:
            try:
                feed = klass(None, request, json=json).get_feed(*args)
            except FeedDoesNotExist:
                raise Http404
            else:
                mime_type = feed.mime_type
                output = feed.writeString('utf-8')
                cache.cache.set(cache_key, (mime_type, output))
        else:
            mime_type, output = mime_type_and_output

        if json and request.GET.get('jsoncallback'):
            output = '%s(%s);' % (
                request.GET['jsoncallback'],
                output)
            mime_type = 'text/javascript'
        if mime_type.startswith('application/') and \
                'MSIE' in request.META.get('HTTP_USER_AGENT', ''):
            # MSIE doesn't support application/atom+xml, so we fake it
            mime_type = 'text/html'
        response = HttpResponse(output,
                            mimetype=mime_type)
        patch_vary_headers(response, ['User-Agent'])
        return response
    return wrapper

class ItemCountMixin(object):
    '''This class contains just an items method.

    It dispatches to self.all_items(), and slices that to match
    either the number requested in self.request.GET['count'] or
    LOCALTV_FEED_LENGTH.'''

    def slice_items(self, items):
        try:
            length = int(self.request.GET.get('count', None))
        except (ValueError, TypeError):
            length = LOCALTV_FEED_LENGTH
        return items[:length]

class ThumbnailFeedGenerator(feedgenerator.Atom1Feed):

    def root_attributes(self):
        attrs = feedgenerator.Atom1Feed.root_attributes(self)
        attrs['xmlns:media'] = 'http://search.yahoo.com/mrss/'
        return attrs

    def add_item_elements(self, handler, item):
        feedgenerator.Atom1Feed.add_item_elements(self, handler, item)
        if 'thumbnail' in item:
            handler.addQuickElement('media:thumbnail',
                                    attrs={'url': item['thumbnail']})
        if 'website_url' in item:
            handler.addQuickElement('link', attrs={
                    'rel': 'via',
                    'href': item['website_url']})
        if 'embed_code' in item:
            handler.startElement('media:player',
                                 {'url': item.get('website_url', '')})
            handler.characters(item['embed_code'])
            handler.endElement('media:player')

class JSONGenerator(feedgenerator.SyndicationFeed):
    mime_type = 'application/json'
    def write(self, outfile, encoding):
        json = {}
        self.add_root_elements(json)
        self.write_items(json)
        simplejson.dump(json, outfile, encoding=encoding)

    def add_root_elements(self, json):
        json['title'] = self.feed['title']
        json['link'] = self.feed['link']
        json['id'] = self.feed['id']
        json['updated'] = unicode(self.latest_post_date())

    def write_items(self, json):
        json['items'] = []
        for item in self.items:
            self.add_item_elements(json['items'], item)

    def add_item_elements(self, json_items, item):
        json_item = {}
        json_item['title'] = item['title']
        json_item['link'] = item['link']
        json_item['when'] = item['when']
        if item.get('pubdate'):
            json_item['pubdate'] = unicode(item['pubdate'])
        if item.get('description'):
            json_item['description'] = item['description']
        if item.get('enclosure'):
            enclosure = item['enclosure']
            json_item['enclosure'] = {
                'link': enclosure.url,
                'length': enclosure.length,
                'type': enclosure.mime_type}
        if item['categories']:
            json_item['categories'] = item['categories']
        if 'thumbnail' in item:
            json_item['thumbnail'] = item['thumbnail']
            json_item['thumbnails_resized'] = resized = []
            for size, url in item['thumbnails_resized'].items():
                resized.append({'width': size[0],
                                'height': size[1],
                                'url': url})
        if 'website_url' in item:
            json_item['website_url'] = item['website_url']
        if 'embed_code' in item:
            json_item['embed_code'] = item['embed_code']

        json_items.append(json_item)


class BaseVideosFeed(Feed, ItemCountMixin):
    title_template = "localtv/feed/title.html"
    description_template = "localtv/feed/description.html"
    feed_type = ThumbnailFeedGenerator

    def __init__(self, *args, **kwargs):
        if 'json' in kwargs:
            if kwargs.pop('json'):
                self.feed_type = JSONGenerator
        Feed.__init__(self, *args, **kwargs)
        self.sitelocation = models.SiteLocation.objects.get_current()

    def item_pubdate(self, video):
        if video.status != models.VIDEO_STATUS_ACTIVE:
            return None
        return video.when().replace(tzinfo=FixedOffset(0))

    def item_guid(self, video):
        if video.guid:
            return video.guid
        return add_domain(video.site.domain, video.get_absolute_url())

    def item_link(self, video):
        return video.get_absolute_url()

    def item_extra_kwargs(self, item):
        kwargs = {
            'when': '%s %s ago' % (
                item.when_prefix(),
                simpletimesince(item.when()))
            }
        if item.website_url:
            kwargs['website_url'] = iri_to_uri(item.website_url)
        if item.has_thumbnail:
            if item.thumbnail_url:
                kwargs['thumbnail'] = iri_to_uri(item.thumbnail_url)
            else:
                default_url = default_storage.url(
                    item.get_resized_thumb_storage_path(375, 295))
                if not (default_url.startswith('http://') or
                        default_url.startswith('https://')):
                    default_url = 'http://%s%s' % (
                    self.sitelocation.site.domain, default_url)
                kwargs['thumbnail'] = default_url
            kwargs['thumbnails_resized'] = resized = {}
            for size in models.THUMB_SIZES:
                url = default_storage.url(
                    item.get_resized_thumb_storage_path(*size))
                if not (url.startswith('http://') or
                        url.startswith('http://')):
                    url = 'http://%s%s' % (
                        self.sitelocation.site.domain, url)
                resized[size] = url
        if item.embed_code:
            kwargs['embed_code'] = item.embed_code
        return kwargs

    def item_enclosure_url(self, video):
        if video.file_url:
            return video.file_url
        elif video.flash_enclosure_url:
            return video.flash_enclosure_url
        # FIXME: The below is a gross hack. It is strictly a workaround for Miro pre-4.0,
        # where if the feed item has no enclosure URL but it has a thumbnail, the feed parser
        # in Miro 4.0 crashes, and no items at all show up in the feed.
        elif video.website_url:
            return video.website_url
        # In the future, the feed views should have tests (I guess they don't, at *all*, as far as I can tell)
        # and we should make sure that we cover the case where the feed has no enclosure URL.
        #
        # In that case, we should make sure to not generate a thumbnail.

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
        return reverse('localtv_list_new')

    def title(self):
        return "%s: %s" % (
            self.sitelocation.site.name, _('New Videos'))

    def items(self):
        videos = models.Video.objects.new(
            site=self.sitelocation.site,
            status=models.VIDEO_STATUS_ACTIVE)
        return self.slice_items(videos)


class FeaturedVideosFeed(BaseVideosFeed):
    def link(self):
        return reverse('localtv_list_featured')

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
        return self.slice_items(videos)

class PopularVideosFeed(BaseVideosFeed):
    def link(self):
        return reverse('localtv_list_popular')

    def items(self):
        videos = models.Video.objects.popular_since(
            datetime.timedelta(days=7), self.sitelocation,
            status=models.VIDEO_STATUS_ACTIVE)
        return self.slice_items(videos)

    def title(self):
        return "%s: %s" % (
            self.sitelocation.site.name, _('Popular Videos'))


class CategoryVideosFeed(BaseVideosFeed):
    def get_object(self, bits):
        return models.Category.objects.get(site=self.sitelocation.site,
                                           slug=bits[0])

    def link(self, category):
        return category.get_absolute_url()

    def items(self, category):
        return self.slice_items(category.approved_set.all())

    def title(self, category):
        return "%s: %s" % (
            self.sitelocation.site.name, _('Category: %s') % category.name)

class AuthorVideosFeed(BaseVideosFeed):
    def get_object(self, bits):
        return User.objects.get(pk=bits[0])

    def link(self, author):
        return reverse('localtv_author', args=[author.pk])

    def items(self, author):
        videos = models.Video.objects.filter(
            Q(authors=author) | Q(user=author),
            site=self.sitelocation.site,
            status=models.VIDEO_STATUS_ACTIVE).distinct()
        return self.slice_items(videos)

    def title(self, author):
        name_or_username = author.get_full_name()
        if not name_or_username.strip():
            name_or_username = author.username

        return "%s: %s" % (
            self.sitelocation.site.name,
            _('Author: %s') % name_or_username)

class TagVideosFeed(BaseVideosFeed):
    def get_object(self, bits):
        return Tag.objects.get(name=bits[0])

    def link(self, tag):
        return reverse('localtv_list_tag', args=[tag.name])

    def items(self, tag):
        videos = models.Video.tagged.with_all(tag).filter(
            site=self.sitelocation.site,
            status=models.VIDEO_STATUS_ACTIVE)
        return self.slice_items(videos)

    def title(self, tag):
        return "%s: %s" % (
            self.sitelocation.site.name, _('Tag: %s') % tag.name)

class SearchVideosFeed(BaseVideosFeed):
    def get_object(self, bits):
        return bits[0]

    def link(self, search):
        args = {'q': search.encode('utf-8')}
        if self.request.GET.get('sort', None) == 'latest':
            args['sort'] = 'latest'
        return reverse('localtv_search') + '?' + urllib.urlencode(args)

    def items(self, search):
        form = VideoSearchForm({'q': search})
        if not form.is_valid():
            raise FeedDoesNotExist(search)
        results = form.search()
        if self.request.GET.get('sort', None) == 'latest':
            videos = models.Video.objects.new(
                site=self.sitelocation.site,
                status=models.VIDEO_STATUS_ACTIVE,
                pk__in=[result.pk for result in results if result])
            return self.slice_items(videos)
        return [result.object for result in self.slice_items(results)
                if result.object]

    def title(self, search):
        return u"%s: %s" % (
            self.sitelocation.site.name, _(u'Search: %s') % search)

class PlaylistVideosFeed(BaseVideosFeed):
    def get_object(self, bits):
        return Playlist.objects.get(pk=bits[0])

    def link(self, playlist):
        return playlist.get_absolute_url()

    def items(self, playlist):
        videos = playlist.video_set.all()
        if self.request.GET.get('sort', None) != 'order':
            videos = videos.order_by('-playlistitem___order')
        return self.slice_items(videos)

    def title(self, playlist):
        return "%s: %s" % (
            self.sitelocation.site.name, _('Playlist: %s') % playlist.name)

new = feed_view(NewVideosFeed)
featured = feed_view(FeaturedVideosFeed)
popular = feed_view(PopularVideosFeed)
category = feed_view(CategoryVideosFeed)
author = feed_view(AuthorVideosFeed)
tag = feed_view(TagVideosFeed)
search = feed_view(SearchVideosFeed)
playlist = feed_view(PlaylistVideosFeed)

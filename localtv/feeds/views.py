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
from django.contrib.sites.models import Site
from django.contrib.syndication.views import Feed, add_domain
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import default_storage
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.utils import feedgenerator
from django.utils.cache import patch_vary_headers
from django.utils.encoding import iri_to_uri, force_unicode
from django.utils.translation import ugettext as _
from django.utils.tzinfo import FixedOffset
from haystack.query import SearchQuerySet
from tagging.models import Tag

from localtv.feeds.feedgenerator import ThumbnailFeedGenerator, JSONGenerator
from localtv.models import Video, Category
from localtv.playlists.models import Playlist
from localtv.search.forms import VideoSearchForm
from localtv.search.utils import SortFilterViewMixin
from localtv.templatetags.filters import simpletimesince


FLASH_ENCLOSURE_STATIC_LENGTH = 1

LOCALTV_FEED_LENGTH = 30

class BaseVideosFeed(Feed, SortFilterViewMixin):
    title_template = "localtv/feed/title.html"
    description_template = "localtv/feed/description.html"
    feed_type = ThumbnailFeedGenerator
    default_sort = None
    default_filter = None

    def __init__(self, json=False):
        if json:
            self.feed_type = JSONGenerator

    def _get_cache_key(self, vary):
        return u'localtv_feed_cache:%(domain)s:%(class)s:%(vary)s' % {
            'domain': Site.objects.get_current().domain,
            'class': self.__class__.__name__,
            'vary': force_unicode(vary).replace(' ', '')
        }

    def __call__(self, request, *args, **kwargs):
        is_json = self.feed_type is JSONGenerator
        jsoncallback = request.GET.get('jsoncallback')
        is_jsonp = is_json and bool(jsoncallback)
        vary = (
            is_json,
            is_jsonp,
            request.GET.get('count'),
            request.GET.get('startIndex'),
            # We need to vary on start-index as well since
            # :meth:`_get_opensearch_data` uses it as an alternate source for
            # startIndex.
            request.GET.get('start-index'),
            request.GET.get('startPage')
        )
        cache_key = self._get_cache_key(vary)

        response = cache.get(cache_key)
        if response is None:
            response = super(BaseVideosFeed, self).__call__(request,
                                                            *args, **kwargs)
            if is_jsonp:
                response = HttpResponse(u"%s(%s);" % (jsoncallback,
                            response.content), mimetype='text/javascript')
            cache.set(cache_key, response, 15*60)
        return response

    def get_object(self, request, *args, **kwargs):
        """
        Returns a dictionary containing all information that must be propagated
        to child methods, since feed instances are reused for multiple requests,
        and are thus unsuitable for storage.

        """
        return {'request': request}

    def _actual_items(self, obj):
        raise NotImplementedError

    def get_feed(self, obj, request):
        """
        Returns a feed generator that has opensearch information stored as
        :attr:`feed.opensearch_data`.

        """
        feed = super(BaseVideosFeed, self).get_feed(obj, request)
        feed.opensearch_data = self._get_opensearch_data(obj)
        return feed

    def items(self, obj):
        """
        Handles a list or queryset of items fetched with :meth:`_actual_items`
        according to the following `OpenSearch` query string parameters:

        * count
        * startIndex
        * startPage

        More info at http://www.opensearch.org/Specifications/OpenSearch/1.1#OpenSearch_1.1_parameters

        """
        sqs = self._query(self._get_query(obj['request']))
        sqs = self._sort(sqs, self._get_sort(obj['request']))
        filter_dict, xxx = self._get_filter_info(obj['request'], [obj.get('obj')])
        sqs, xxx = self._filter(sqs, **filter_dict)

        opensearch = self._get_opensearch_data(obj)
        start = opensearch['startindex']
        end = start + opensearch['itemsperpage']
        opensearch['totalresults'] = len(sqs)
        sqs = sqs.load_all()[start:end]
        return [result.object for result in sqs]

    def _get_opensearch_data(self, obj):
        """
        Stores and returns opensearch information for the object.

        """
        if 'opensearch_data' not in obj:
            request = obj['request']

            count = self._normalize_param(request, 'count',
                                default=LOCALTV_FEED_LENGTH)

            # The spec says to use startIndex, but vidscraper seems to send out
            # start-index. I don't really know what's up with that.
            startIndex = self._normalize_param(request, 'startIndex',
                                    default=None)
            if startIndex is None:
                startIndex = self._normalize_param(request, 'start-index')
            # The spec allows negative values, but that seems useless to me,
            # so we will insist on non-negative values.

            # We only check for startPage if there is no startIndex. This
            # mailing list discussion indicates that startPage and startIndex
            # conflict:
            # http://lists.opensearch.org/pipermail/opensearch-discuss/2006-December/000026.html

            if not startIndex:
                startPage = self._normalize_param(request, 'startPage')
                startIndex = startPage * count

            obj['opensearch_data'] = {'startindex': startIndex,
                                    'itemsperpage': count}
        return obj['opensearch_data']

    def _normalize_param(self, request, param, default=0,
                                allow_negative=False):
        try:
            value = int(request.GET.get(param, None))
        except (ValueError, TypeError):
            value = default

        if not allow_negative:
            if value < 0:
                value = default

        return value

    def item_pubdate(self, video):
        if not video.is_active():
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
            site = Site.objects.get_current()
            if item.thumbnail_url:
                kwargs['thumbnail'] = iri_to_uri(item.thumbnail_url)
            else:
                default_url = default_storage.url(
                    item.get_resized_thumb_storage_path(375, 295))
                if not (default_url.startswith('http://') or
                        default_url.startswith('https://')):
                    default_url = 'http://%s%s' % (site.domain, default_url)
                kwargs['thumbnail'] = default_url
            kwargs['thumbnails_resized'] = resized = {}
            for size in Video.THUMB_SIZES:
                url = default_storage.url(
                    item.get_resized_thumb_storage_path(*size))
                if not (url.startswith('http://') or
                        url.startswith('http://')):
                    url = 'http://%s%s' % (site.domain, url)
                resized[size] = url
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
    default_sort = '-date'

    def link(self):
        return reverse('localtv_list_new')

    def title(self):
        return "%s: %s" % (
            Site.objects.get_current().name, _('New Videos'))


class FeaturedVideosFeed(BaseVideosFeed):
    default_sort = '-featured'

    def link(self):
        return reverse('localtv_list_featured')

    def title(self):
        return "%s: %s" % (
            Site.objects.get_current().name, _('Featured Videos'))


class PopularVideosFeed(BaseVideosFeed):
    default_sort = '-popular'

    def link(self):
        return reverse('localtv_list_popular')

    def title(self):
        return "%s: %s" % (
            Site.objects.get_current().name, _('Popular Videos'))


class CategoryVideosFeed(BaseVideosFeed):
    default_filter = 'category'
    default_sort = '-date'

    def get_object(self, request, slug):
        obj = BaseVideosFeed.get_object(self, request, slug)
        obj['obj'] = Category.objects.get(
                        site=Site.objects.get_current(), slug=slug)
        return obj

    def link(self, obj):
        return obj['obj'].get_absolute_url()

    def title(self, obj):
        return "%s: %s" % (
            Site.objects.get_current().name,
            _('Category: %s') % obj['obj'].name
        )

class AuthorVideosFeed(BaseVideosFeed):
    default_filter = 'author'
    default_sort = '-date'

    def get_object(self, request, pk):
        obj = BaseVideosFeed.get_object(self, request, pk)
        obj['obj'] = User.objects.get(pk=pk)
        return obj

    def link(self, obj):
        return reverse('localtv_author', args=[obj['obj'].pk])

    def title(self, obj):
        name_or_username = obj['obj'].get_full_name()
        if not name_or_username.strip():
            name_or_username = obj['obj'].username

        return "%s: %s" % (
            Site.objects.get_current().name,
            _('Author: %s') % name_or_username)


class FeedVideosFeed(BaseVideosFeed):
    # This class can be a bit confusing:
    #
    # It is the Miro Community feed that represents all
    # the videos that we have imported from a remote video source.
    #
    # To avoid end-users getting confused, the URL does not say "feed"
    # twice, but talks about video sources.
    default_filter = 'feed'
    default_sort = '-date'

    def get_object(self, request, pk):
        obj = BaseVideosFeed.get_object(self, request, pk)
        obj['obj'] = Feed.objects.get(pk=pk)
        return obj

    def link(self, obj):
        return reverse('localtv_list_feed', args=[obj['obj'].pk])

    def title(self, obj):
        return "%s: Videos imported from %s" % (
            Site.objects.get_current().name,
            obj['obj'].name or '')


class TagVideosFeed(BaseVideosFeed):
    default_filter = 'tag'
    default_sort = '-date'

    def get_object(self, request, name):
        obj = BaseVideosFeed.get_object(self, request, name)
        obj['obj'] = Tag.objects.get(name=name)
        return obj

    def link(self, obj):
        return reverse('localtv_list_tag', args=[obj['obj'].name])

    def title(self, obj):
        return "%s: %s" % (
            Site.objects.get_current().name, _('Tag: %s') % obj['obj'].name)


class SearchVideosFeed(BaseVideosFeed):
    def get_object(self, request, query):
        obj = BaseVideosFeed.get_object(self, request, query)
        obj['obj'] = query
        return obj

    def link(self, obj):
        kwargs = {'q': obj['obj'].encode('utf-8')}
        sort = obj['request'].GET.get('sort', None)
        if sort == 'latest':
            kwargs['sort'] = 'latest'
        return u"?".join((reverse('localtv_search'), urllib.urlencode(args)))

    def title(self, obj):
        return u"%s: %s" % (
            Site.objects.get_current().name, _(u'Search: %s') % obj['obj'])


class PlaylistVideosFeed(BaseVideosFeed):
    def get_object(self, request, pk):
        obj = BaseVideosFeed.get_object(self, request, pk)
        obj['obj'] = Playlist.objects.get(pk=pk)
        return obj

    def link(self, obj):
        return obj['obj'].get_absolute_url()

    def items(self, obj):
        """
        This feed is unusual enough that we actually need to override
        :meth:`items`.

        """
        sort = self._get_sort(obj['request'])
        if sort == 'order':
            # TODO: This probably breaks if a video is in multiple playlists.
            # Check.
            videos = obj['obj'].video_set.order_by('-playlistitem___order')
            opensearch = self._get_opensearch_data(obj)
            start= opensearch['startindex']
            end = start + opensearch['itemsperpage']
            opensearch['totalresults'] = len(videos)
            videos = videos[start:end]
            return videos
        return BaseVideosFeed.items(self, obj)

    def title(self, obj):
        return "%s: %s" % (
            Site.objects.get_current().name,
            _('Playlist: %s') % obj['obj'].name)

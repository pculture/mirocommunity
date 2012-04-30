# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2009, 2010, 2011, 2012 Participatory Culture Foundation
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

from hashlib import sha1
import urllib

from daguerre.models import AdjustedImage, Image
from django.contrib.sites.models import Site
from django.contrib.syndication.views import Feed as FeedView, add_domain
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.utils.encoding import iri_to_uri, force_unicode
from django.utils.translation import ugettext as _
from django.utils.tzinfo import FixedOffset

from localtv.feeds.feedgenerator import ThumbnailFeedGenerator, JSONGenerator
from localtv.models import Video
from localtv.search.utils import NormalizedVideoList
from localtv.search.views import SortFilterMixin
from localtv.templatetags.filters import simpletimesince


FLASH_ENCLOSURE_STATIC_LENGTH = 1

LOCALTV_FEED_LENGTH = 30

class BaseVideosFeed(FeedView, SortFilterMixin):
    title_template = "localtv/feed/title.html"
    description_template = "localtv/feed/description.html"
    feed_type = ThumbnailFeedGenerator

    def __init__(self, json=False):
        if json:
            self.feed_type = JSONGenerator

    def _get_cache_key(self, request, vary):
        return u'localtv_feed_cache:%(domain)s:%(class)s:%(vary)s' % {
            'domain': Site.objects.get_current().domain,
            'class': self.__class__.__name__,
            'vary': sha1(force_unicode(vary).replace(' ', '')).hexdigest(),
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
            request.GET.get('startPage'),
            repr(args),
            repr(kwargs),
        )
        cache_key = self._get_cache_key(request, vary)

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
        form = self.form_class(self._request_form_data(request, **kwargs))
        if not form.is_valid():
            raise Http404

        obj = {
            'request': request,
            'form': form,
        }

        if self.url_filter is not None:
            try:
                obj['obj'] = form.cleaned_data[self.url_filter][0]
            except IndexError:
                raise Http404

        return obj

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
        qs = obj['form'].get_queryset()
        items = NormalizedVideoList(qs)
        return self._opensearch_items(items, obj)

    def _opensearch_items(self, items, obj):
        opensearch = self._get_opensearch_data(obj)
        start = opensearch['startindex']
        end = start + opensearch['itemsperpage']
        opensearch['totalresults'] = len(items)
        return items[start:end]

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
        if not video.status == Video.ACTIVE:
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
                thumbnail_url = iri_to_uri(item.thumbnail_url)
            else:
                try:
                    image = Image.objects.for_storage_path(
                                item.thumbnail_path)
                except Image.DoesNotExist:
                    thumbnail_url = ''
                else:
                    adjusted = AdjustedImage.objects.adjust(image, 375, 295)
                    thumbnail_url = adjusted.adjusted.url
                    if not (thumbnail_url.startswith('http://') or
                            thumbnail_url.startswith('https://')):
                        thumbnail_url = 'http://%s%s' % (site.domain,
                                                         thumbnail_url)
            kwargs['thumbnail'] = thumbnail_url
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
        return u"%s: %s" % (
            Site.objects.get_current().name, _('New Videos'))


class FeaturedVideosFeed(BaseVideosFeed):
    default_sort = '-featured'

    def link(self):
        return reverse('localtv_list_featured')

    def title(self):
        return u"%s: %s" % (
            Site.objects.get_current().name, _('Featured Videos'))


class PopularVideosFeed(BaseVideosFeed):
    default_sort = '-popular'

    def link(self):
        return reverse('localtv_list_popular')

    def title(self):
        return u"%s: %s" % (
            Site.objects.get_current().name, _('Popular Videos'))


class CategoryVideosFeed(BaseVideosFeed):
    url_filter = 'category'
    url_filter_kwarg = 'slug'
    default_sort = '-date'

    def link(self, obj):
        return obj['obj'].get_absolute_url()

    def title(self, obj):
        return u"%s: %s" % (
            Site.objects.get_current().name,
            _(u'Category: %s') % force_unicode(obj['obj'].name)
        )

class AuthorVideosFeed(BaseVideosFeed):
    url_filter = 'author'
    default_sort = '-date'

    def link(self, obj):
        return reverse('localtv_author', args=[obj['obj'].pk])

    def title(self, obj):
        name_or_username = obj['obj'].get_full_name()
        if not name_or_username.strip():
            name_or_username = obj['obj'].username

        return u"%s: %s" % (
            Site.objects.get_current().name,
            _(u'Author: %s') % force_unicode(name_or_username))


class FeedVideosFeed(BaseVideosFeed):
    # This class can be a bit confusing:
    #
    # It is the Miro Community feed that represents all
    # the videos that we have imported from a remote video source.
    #
    # To avoid end-users getting confused, the URL does not say "feed"
    # twice, but talks about video sources.
    url_filter = 'feed'
    default_sort = '-date'

    def link(self, obj):
        return reverse('localtv_list_feed', args=[obj['obj'].pk])

    def title(self, obj):
        return u"%s: Videos imported from %s" % (
            Site.objects.get_current().name,
            force_unicode(obj['obj'].name) or '')


class TagVideosFeed(BaseVideosFeed):
    url_filter = 'tag'
    url_filter_kwarg = 'name'
    default_sort = '-date'

    def link(self, obj):
        return reverse('localtv_list_tag', args=[obj['obj'].name])

    def title(self, obj):
        return u"%s: %s" % (Site.objects.get_current().name,
                          _(u'Tag: %s') % force_unicode(obj['obj'].name))


class SearchVideosFeed(BaseVideosFeed):

    def _get_cache_key(self, request, vary):
        key = super(SearchVideosFeed, self)._get_cache_key(request, vary)
        if request.GET.get('sort', None) == 'latest':
            return '%s:latest' % key
        return key

    def get_object(self, request, query):
        obj = BaseVideosFeed.get_object(self, request, query)
        obj['obj'] = query
        return obj

    def _get_query(self, request):
        # HACK to pull the query out of the path
        return request.path.rsplit('/', 1)[1]

    def link(self, obj):
        args = {'q': obj['obj'].encode('utf-8')}
        sort = obj['request'].GET.get('sort', None)
        if sort == 'latest':
            args['sort'] = 'latest'
        return u"?".join((reverse('localtv_search'), urllib.urlencode(args)))

    def title(self, obj):
        return u"%s: %s" % (
            Site.objects.get_current().name,
            _(u'Search: %s') % force_unicode(obj['obj']))


class PlaylistVideosFeed(BaseVideosFeed):
    url_filter = 'playlist'

    def _get_cache_key(self, request, vary):
        key = super(PlaylistVideosFeed, self)._get_cache_key(request, vary)
        if request.GET.get('sort', None) == 'order':
            return '%s:order' % key
        return key

    def link(self, obj):
        return obj['obj'].get_absolute_url()

    def _request_form_data(self, request, **kwargs):
        data = super(PlaylistVideosFeed, self)._request_form_data(request, **kwargs)
        if data.get('sort') in ('order', '-order'):
            # This HACK helps us sort by playlist order.
            data.pop('sort')
        return data

    def get_object(self, request, *args, **kwargs):
        obj = super(PlaylistVideosFeed, self).get_object(request, *args,
                                                         **kwargs)
        if request.GET.get('sort') in ('order', '-order'):
            # This HACK helps us sort by playlist order.
            obj['playlist_order'] = request.GET['sort']
        return obj

    def items(self, obj):
        """
        This feed is unusual enough that we actually need to override
        :meth:`items`.

        """
        form = obj['form']
        # We currently don't support searching combined with the 'order' sort.
        if 'playlist_order' in obj:
            # This is a HACK for backwards-compatibility.
            order_by = '{0}playlistitem___order'.format(
                               '' if obj['playlist_order'][0] == '-' else '-')
            queryset = obj['obj'].items.order_by(order_by)
        else:
            queryset = form._search()
            queryset = form._sort(queryset)
        queryset = NormalizedVideoList(form._filter(queryset))
        return self._opensearch_items(queryset, obj)

    def title(self, obj):
        return u"%s: %s" % (
            Site.objects.get_current().name,
            _(u'Playlist: %s') % force_unicode(obj['obj'].name))

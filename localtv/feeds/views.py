from hashlib import sha1

from daguerre.utils.adjustments import BulkAdjustmentHelper
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
from localtv.search.forms import ModelFilterField
from localtv.search.utils import NormalizedVideoList
from localtv.search.views import SortFilterMixin
from localtv.templatetags.filters import simpletimesince, full_url


FLASH_ENCLOSURE_STATIC_LENGTH = 1
LOCALTV_FEED_LENGTH = 30
THUMBNAIL_SIZES = (
    (375, 295), # largest thumbnail (thumbnail_url)
    (222, 169), # large thumbnail (description thumbnail)
    (140, 110), # medium thumbnail (widget only)
    (88, 68),   # small thumbnail (widget only)
)


class BaseVideosFeed(FeedView, SortFilterMixin):
    title_template = "localtv/feed/title.html"
    description_template = "localtv/feed/description.html"
    feed_type = ThumbnailFeedGenerator
    view_name = None
    filter_kwarg = 'pk'

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
        # Vary on search/sort/filter parameters, as well.
        vary += tuple(request.GET.get(name)
                      for name in self.form_class.base_fields)
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
        obj = {
            'request': request
        }

        if self.filter_name is not None:
            field = self.form_class.base_fields[self.filter_name]
            if isinstance(field, ModelFilterField):
                model = field.queryset.model
                try:
                    key = field.to_field_name or 'pk'
                    obj['obj'] = model.objects.get(**{
                                              key: kwargs[self.filter_kwarg]})
                except (ValueError, model.DoesNotExist):
                    raise Http404

        return obj

    def get_form_data(self, base_data=None, filter_value=None):
        data = super(BaseVideosFeed, self).get_form_data(base_data,
                                                         filter_value)
        if data.get('sort') == 'latest':
            data['sort'] = 'newest'
        return data

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

    def _base_link(self, obj):
        if self.view_name is not None:
            return reverse(self.view_name)
        elif 'obj' in obj:
            return obj['obj'].get_absolute_url()
        else:
            raise NotImplementedError

    def link(self, obj):
        return u"?".join((self._base_link(obj),
                          obj['request'].GET.urlencode()))

    def items(self, obj):
        """
        Handles a list or queryset of items fetched with :meth:`_actual_items`
        according to the following `OpenSearch` query string parameters:

        * count
        * startIndex
        * startPage

        More info at http://www.opensearch.org/Specifications/OpenSearch/1.1#OpenSearch_1.1_parameters

        """
        filter_value = obj.get('obj')
        if self.filter_name is not None:
            field = self.form_class.base_fields[self.filter_name]
            if isinstance(field, ModelFilterField):
                filter_value = [filter_value]
        form = self.get_form(obj['request'].GET.dict(), filter_value)
        items = NormalizedVideoList(form.search())
        items = self._opensearch_items(items, obj)
        return self._bulk_adjusted_items(items)

    def _opensearch_items(self, items, obj):
        opensearch = self._get_opensearch_data(obj)
        start = opensearch['startindex']
        end = start + opensearch['itemsperpage']
        opensearch['totalresults'] = len(items)
        return items[start:end]

    def _bulk_adjusted_items(self, items):
        if self.feed_type is JSONGenerator:
            sizes = THUMBNAIL_SIZES
        else:
            sizes = THUMBNAIL_SIZES[:2]
        for size in sizes:
            helper = BulkAdjustmentHelper(items,
                                          "thumbnail",
                                          width=size[0],
                                          height=size[1],
                                          adjustment='fill')
            for item, info_dict in helper.info_dicts():
                # Set a private attribute so we can retrieve this later.
                if not hasattr(item, '_adjusted'):
                    item._adjusted = {}
                item._adjusted[size] = info_dict
        # set the default adjustment as a public attribute so that it
        # can be accessed from the description template.
        for item in items:
            item.description_thumbnail = item._adjusted[THUMBNAIL_SIZES[1]]
        return items

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
        # adjusted is set in self._bulk_adjusted_items.
        if not item._adjusted[THUMBNAIL_SIZES[0]]:
            kwargs['thumbnail_url'] = ''
        else:
            url = full_url(item._adjusted[THUMBNAIL_SIZES[0]]['url'])
            kwargs['thumbnail'] = iri_to_uri(url)

            if self.feed_type is JSONGenerator:
                # Version 2 of the MC widgets expect a
                # 'thumbnails_resized' argument which includes thumbnails
                # of these sizes for the various sizes of widget. These
                # are only here for backwards compatibility with those
                # widgets.
                kwargs['thumbnails_resized'] = []

                for size in THUMBNAIL_SIZES[1:]:
                    info_dict = item._adjusted.get(size, {})
                    url = full_url(info_dict.get('url', ''))
                    kwargs['thumbnails_resized'].append({'width': size[0],
                                                         'height': size[1],
                                                         'url': url})
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
    view_name = 'localtv_list_new'
    sort = 'newest'

    def title(self):
        return u"%s: %s" % (
            Site.objects.get_current().name, _('New Videos'))


class FeaturedVideosFeed(BaseVideosFeed):
    view_name = 'localtv_list_featured'
    sort = 'featured'

    def title(self):
        return u"%s: %s" % (
            Site.objects.get_current().name, _('Featured Videos'))


class PopularVideosFeed(BaseVideosFeed):
    view_name = 'localtv_list_popular'
    sort = 'popular'

    def title(self):
        return u"%s: %s" % (
            Site.objects.get_current().name, _('Popular Videos'))


class CategoryVideosFeed(BaseVideosFeed):
    filter_name = 'category'
    filter_kwarg = 'slug'

    def title(self, obj):
        return u"%s: %s" % (
            Site.objects.get_current().name,
            _(u'Category: %s') % force_unicode(obj['obj'].name)
        )

class AuthorVideosFeed(BaseVideosFeed):
    filter_name = 'author'

    def _base_link(self, obj):
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
    filter_name = 'feed'

    def _base_link(self, obj):
        return reverse('localtv_list_feed', args=[obj['obj'].pk])

    def title(self, obj):
        return u"%s: Videos imported from %s" % (
            Site.objects.get_current().name,
            force_unicode(obj['obj'].name) or '')


class TagVideosFeed(BaseVideosFeed):
    filter_name = 'tag'
    filter_kwarg = 'name'

    def _base_link(self, obj):
        return reverse('localtv_list_tag', args=[obj['obj'].name])

    def title(self, obj):
        return u"%s: %s" % (Site.objects.get_current().name,
                          _(u'Tag: %s') % force_unicode(obj['obj'].name))


class SearchVideosFeed(BaseVideosFeed):
    view_name = 'localtv_search'

    def get_form_data(self, base_data=None, filter_value=None):
        data = super(SearchVideosFeed, self).get_form_data(base_data)
        data['q'] = filter_value
        return data

    def get_object(self, request, query):
        obj = BaseVideosFeed.get_object(self, request, query=query)
        obj['obj'] = query
        return obj

    def title(self, obj):
        return u"%s: %s" % (
            Site.objects.get_current().name,
            _(u'Search: %s') % force_unicode(obj['obj']))


class PlaylistVideosFeed(BaseVideosFeed):
    filter_name = 'playlist'

    def get_form_data(self, base_data=None, filter_value=None):
        data = super(PlaylistVideosFeed, self).get_form_data(base_data,
                                                             filter_value)
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
        form = self.get_form(obj['request'].GET.dict(), [obj.get('obj')])
        # We currently don't support searching combined with the 'order' sort.
        if 'playlist_order' in obj:
            # This is a HACK for backwards-compatibility.
            order_by = '{0}playlistitem___order'.format(
                               '-' if obj['playlist_order'][0] == '-' else '')
            items = obj['obj'].items.order_by(order_by)
            items = form._filter(items)
        else:
            items = form.search()
        items = NormalizedVideoList(items)
        items = self._opensearch_items(items, obj)
        return self._bulk_adjusted_items(items)

    def title(self, obj):
        return u"%s: %s" % (
            Site.objects.get_current().name,
            _(u'Playlist: %s') % force_unicode(obj['obj'].name))

import datetime
import hashlib
import string
import urllib
import urllib2
import types
import os
import os.path
import logging

from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.db.models import get_model, Q
from django.db.models.query import QuerySet
from django.utils.encoding import force_unicode, smart_str
import tagging
import vidscraper
from notification import models as notification

from localtv.settings import API_KEYS


def get_tag(tag_text, using='default'):
    while True:
        try:
            tags = tagging.models.Tag.objects.using(using).filter(
                name=tag_text)
            if not tags.count():
                return tagging.models.Tag.objects.using(using).create(
                    name=tag_text)
            elif tags.count() == 1:
                return tags[0]
            else:
                for tag in tags:
                    if tag.name == tag:
                        # MySQL doesn't do case-sensitive equals on strings
                        return tag
        except Exception:
            pass # try again to create the tag


def edit_string_for_tags(tag_list):
    """
    Converts a list of tagging.Tag instances into an edit string. Thin wrapper
    around :func:`tagging.utils.edit_string_for_tags` to fix some decoding
    bugs.

    """
    for tag in tag_list:
        tag.name = force_unicode(tag.name)
    edit_string = tagging.utils.edit_string_for_tags(tag_list)

    # HACK to work around a bug in django-tagging.
    if (len(tag_list) == 1 and edit_string == tag_list[0].name
        and " " in edit_string):
        edit_string = '"%s"' % edit_string
    return edit_string


def get_or_create_tags(tag_list, using='default'):
    tag_set = set()
    for tag_text in tag_list:
        if isinstance(tag_text, basestring):
            tag_text = tag_text[:50] # tags can only by 50 chars
        if settings.FORCE_LOWERCASE_TAGS:
            tag_text = tag_text.lower()
        tag = get_tag(tag_text, using)
        tag_set.add(tag)
    return edit_string_for_tags(list(tag_set))


def hash_file_obj(file_obj, hash_constructor=hashlib.sha1, close_it=True):
    hasher = hash_constructor()
    for chunk in iter(lambda: file_obj.read(4096), ''):
        hasher.update(chunk)
    if close_it:
        file_obj.close()
    return hasher.hexdigest()


def unicode_set(iterable):
    output = set()
    for thing in iterable:
        output.add(force_unicode(thing, strings_only=True))
    return output


def get_vidscraper_video(url):
    cache_key = 'vidscraper_data-' + url
    if len(cache_key) >= 250:
        # too long, use the hash
        cache_key = 'vidscraper_data-hash-' + hashlib.sha1(url).hexdigest()
    vidscraper_video = cache.get(cache_key)

    if not vidscraper_video:
        # try and scrape the url
        try:
            vidscraper_video = vidscraper.auto_scrape(url, api_keys=API_KEYS)
        except (vidscraper.exceptions.VidscraperError, urllib2.URLError):
            vidscraper_video = None

        cache.add(cache_key, vidscraper_video)

    return vidscraper_video


def normalize_newlines(s):
    if type(s) in types.StringTypes:
        s = s.replace('\r\n', '\n')
    return s


def send_notice(notice_label, subject, message, fail_silently=True,
                site_settings=None, content_subtype=None):
    notice_type = notification.NoticeType.objects.get(label=notice_label)
    recipient_list = notification.NoticeSetting.objects.filter(
        notice_type=notice_type,
        medium="1",
        send=True).exclude(user__email='').filter(
        Q(user__in=site_settings.admins.all()) |
        Q(user__is_superuser=True)).values_list('user__email', flat=True)
    message = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL,
                           bcc=recipient_list)
    if content_subtype:
        message.content_subtype = content_subtype
    message.send(fail_silently=fail_silently)

class SortHeaders:
    def __init__(self, request, headers, default_order=None):
        self.request = request
        self.header_defs = headers
        if default_order is None:
            for header, ordering in headers:
                if ordering is not None:
                    default_order = ordering
                    break
        self.default_order = default_order
        if default_order.startswith('-'):
            self.desc = True
            self.ordering = default_order[1:]
        else:
             self.desc = False
             self.ordering = default_order

        # Determine order field and order type for the current request
        sort = request.GET.get('sort', '')
        desc = False
        if sort.startswith('-'):
            desc = True
            sort = sort[1:]
        if sort:
            for header, ordering in headers:
                if ordering and ordering.startswith('-'):
                    ordering = ordering[1:]
                if sort == ordering:
                    self.ordering, self.desc = sort, desc

    def headers(self):
        """
        Generates dicts containing header and sort link details for
        all defined headers.
        """
        for header, ordering in self.header_defs:
            css_class = ''
            if ordering == self.ordering or (
                ordering and ordering.startswith('-') and
                ordering[1:] == self.ordering):
                # current sort
                if self.desc:
                    ordering = self.ordering
                    css_class = 'sortup'
                else:
                    ordering = '-%s' % self.ordering
                    css_class = 'sortdown'
            yield {
                'sort': ordering,
                'link': self._query_string(ordering),
                'label': header,
                'class': css_class
                }

    def __iter__(self):
        return iter(self.headers())

    def __len__(self):
        return len(self.header_defs)

    def _query_string(self, sort):
        """
        Creates a query string from the given dictionary of
        parameters, including any additonal parameters which should
        always be present.
        """
        if sort is None:
            return None
        params = self.request.GET.copy()
        params.pop('sort', None)
        params.pop('page', None)
        if sort != self.default_order:
            params['sort'] = sort
        if not params:
            return self.request.path
        return '?%s' % params.urlencode()

    def order_by(self):
        """
        Creates an ordering criterion based on the current order
        field and order type, for use with the Django ORM's
        ``order_by`` method.
        """
        return '%s%s' % (
            self.desc and '-' or '',
            self.ordering)


class SharedQuerySet(QuerySet):
    """
    A QuerySet subclass which returns itself when cloned with :meth:`all`.
    This is designed to be used to generate choices for forms in formsets to
    spare queries, and is probably not suitable for more complex situations.

    """
    def all(self, *args, **kwargs):
        return self


class MockQueryset(object):
    """
    Wrap a list of objects in an object which pretends to be a QuerySet.
    """

    def __init__(self, objects, model=None, filters=None):
        self.objects = objects
        self.model = model
        self.filters = filters or {}
        if self.model:
            self.db = model.objects.all().db
        elif hasattr(objects, 'db'):
            self.db = objects.db
        else:
            self.db = 'default'

        self._count = None
        self._iter_index = None
        self._result_cache = []
        self.ordered = True

    def all(self):
        return self

    def _clone(self):
        return self

    def __len__(self):
        if self._count is None:
            if self.model:
                self._count = self.model.objects.filter(
                    pk__in=self.objects).count()
            else:
                self._count = len(self.objects)
        return self._count

    def __iter__(self):
        if not self.model:
            return iter(self.objects)

        it = MockQueryset(self.objects, self.model, self.filters)
        it._count = self._count
        it._result_cache = self._result_cache[:]
        it._iter_index = 0
        return it

    def next(self):
        if self._iter_index is None:
            raise RuntimeError('Cannot use MockQueryset directly as an '
                               'iterator, must call iter() first')
        if self._iter_index == len(self):
            raise StopIteration # don't even bother looking for more results

        if self._iter_index >= len(self._result_cache): # not enough data
            objs = []
            while True:
                next = self.objects[self._iter_index:self._iter_index + 20]
                if not next:
                    break
                values = self.model.objects.in_bulk(next)
                objs = [values[k] for k in next
                        if k in values and \
                            self._is_valid(values[k])]
                if objs:
                    break
            self._result_cache += objs

        if self._iter_index >= len(self._result_cache):
            raise StopIteration

        result = self._result_cache[self._iter_index]
        self._iter_index += 1

        return result

    def _is_valid(self, obj):
        if not self.filters:
            return True
        for filter_key, filter_value in self.filters.items():
            if getattr(obj, filter_key) != filter_value:
                return False
        return True

    def __getitem__(self, k):
        if isinstance(k, slice):
            mq = MockQueryset(self.objects[k], self.model, self.filters)
            return mq
        return self.objects[k]

    def filter(self, **kwargs):
        new_filters = self.filters.copy()
        for k, v in kwargs.items():
            if '__' in k: # special filter
                return self.objects.filter(**kwargs)
            new_filters[k] = v
        return MockQueryset(self.objects, self.model, new_filters)


def get_profile_model():
    app_label, model_name = settings.AUTH_PROFILE_MODULE.split('.')
    Profile = get_model(app_label, model_name)
    if Profile is None:
        raise RuntimeError("could not find a Profile model at %r" %
                           settings.AUTH_PROFILE_MODULE)
    return Profile


SAFE_URL_CHARACTERS = string.ascii_letters + string.punctuation


def quote_unicode_url(url):
    return urllib.quote(url, safe=SAFE_URL_CHARACTERS)


def touch(filename, override_date=None):
    '''This is like /usr/bin/touch

    It has a special override_date parameter which is used
    as the time to store in the file. If the file is already
    newer than the given time, then we simply do nothing.'''
    actually_touch_it = True

    if override_date:
        as_int = int(override_date.strftime("%s"))
        actually_touch_it = True
        try:
            current_mtime = os.stat(filename).st_mtime
        except OSError, e:
            if e.errno == 2:
                pass # this is expected sometimes
            else:
                logging.error(e)
        else:
            # If the file is already newer, do not touch
            if current_mtime > as_int:
                actually_touch_it = False

    if not actually_touch_it:
        return

    # Okay, so we definitely want to touch the file.
    file_obj = open(filename, 'w')
    file_obj.write('')
    file_obj.close()

    if override_date:
        os.utime(filename, (as_int, as_int))


class UploadTo(object):
    """
    Generates upload paths based on a string format, but makes sure they
    are short enough to fit in a FileField. See django bug 11027:
    https://code.djangoproject.com/ticket/11027

    """
    def __init__(self, upload_to, storage=None, max_length=100):
        self.upload_to = upload_to
        self.storage = storage or default_storage
        self.max_length = max_length

    def __call__(self, instance, filename):
        # Off the bat, leave extra space for potential collisions.
        max_left = self.max_length - 5
        dir_name = os.path.normpath(force_unicode(datetime.datetime.now().strftime(smart_str(self.upload_to))))
        max_left = max_left - len(dir_name)
        if max_left < 6:
            raise ValueError("upload_to is too long.")
        basename, ext = os.path.splitext(filename)
        max_left = max_left - len(ext)
        if max_left < 1:
            raise ValueError("filename is too long")
        if len(basename) > max_left:
            basename = hashlib.sha1(unicode(datetime.datetime.now()) + unicode(filename)).hexdigest()[:max_left]
        return os.path.join(dir_name, "".join((basename, ext)))

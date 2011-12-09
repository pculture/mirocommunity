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

import hashlib
import re
import string
import urllib
import types
import os
import os.path
import logging
import urlparse

import Image
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.db.models import get_model, Q
from django.utils.encoding import force_unicode
from django.core.files.base import ContentFile

import tagging
import vidscraper
from notification import models as notification


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


def get_or_create_tags(tag_list, using='default'):
    tag_set = set()
    for tag_text in tag_list:
        if isinstance(tag_text, basestring):
            tag_text = tag_text[:50] # tags can only by 50 chars
        if settings.FORCE_LOWERCASE_TAGS:
            tag_text = tag_text.lower()
        tag = get_tag(tag_text, using);
        tag.name = force_unicode(tag.name)
        tag_set.add(tag)
    edit_string = tagging.utils.edit_string_for_tags(list(tag_set))

    # HACK to work around a bug in django-tagging.
    if (len(tag_set) == 1 and edit_string == tag_set.pop().name
        and " " in edit_string):
        edit_string = '"%s"' % edit_string
    return edit_string


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
            vidscraper_video = vidscraper.auto_scrape(url)
        except vidscraper.errors.Error:
            vidscraper_video = None

        cache.add(cache_key, vidscraper_video)

    return vidscraper_video


def normalize_newlines(s):
    if type(s) in types.StringTypes:
        s = s.replace('\r\n', '\n')
    return s


def send_notice(notice_label, subject, message, fail_silently=True,
                sitelocation=None, content_subtype=None):
    notice_type = notification.NoticeType.objects.get(label=notice_label)
    recipient_list = notification.NoticeSetting.objects.filter(
        notice_type=notice_type,
        medium="1",
        send=True).exclude(user__email='').filter(
        Q(user__in=sitelocation.admins.all()) |
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


try:
    import backends
except ImportError:
    import storages.backends as backends


try:
    import backends.s3
except (AttributeError, ImportError):
    pass
else:
    class SimplerS3Storage(backends.s3.S3Storage):
        EVEN = set(['0', '2', '4', '6', '8', 'a', 'c', 'e'])
        ODD  = set(['1', '3', '5', '7', '8', 'b', 'd', 'f'])
        '''This is just like the normal S3Storage backend, only
        we override the get_available_name method so that we permit
        ourselves to overwrite files. By default, the core of Django's
        storage layer refuses to overwrite files.'''

        def get_available_name(self, name):
            """ Overwrite existing file with the same name. """
            name = self._clean_name(name)
            return name

        def url(self, *args, **kwargs):
            '''This is just like the S3Storage url() function, with
            one big caveat: It swaps out the default Amazon domain name
            with a nearly-randomly chosen selection of alternate domain names.

            This is to let browsers download with greater parallelism.

            This is kind of like making up a CallingFormat.RoundRobin class,
            but more of a hack. Read this URL for more about CallingFormat:
            https://bitbucket.org/david/django-storages/src/629607f8767f/storages/backends/s3.py'''
            url = super(SimplerS3Storage, self).url(*args, **kwargs)
            if getattr(settings, 'LOCALTV_S3_ROUND_ROBIN', False):
                url = self._maybe_mangle_s3_url(url)
            return url

        def _maybe_mangle_s3_url(self, url):
            '''Input: A URL on Amazon S3.

            Output: One of 2 equivalent URLs to the same file. This function will
            always return the same output for a given input.'''
            hasher = hashlib.md5()
            parsed = list(urlparse.urlparse(url))
            path = parsed[2]
            hasher.update(path)
            digested = hasher.hexdigest()
            if digested[-1] in self.EVEN:
                return url
            else:
                return self._mangle_s3_url(parsed)


        def _mangle_s3_url(self, parsed_url):
            '''This converts the calling format between subdomain to bucket-name.'''
            netloc = parsed_url[1]
            path   = parsed_url[2]
            bucket = settings.AWS_STORAGE_BUCKET_NAME
            S3_DOMAIN = 's3.amazonaws.com'
            if netloc == (bucket + '.' + S3_DOMAIN):
                netloc = S3_DOMAIN
                path = '/' + bucket + path
            elif (path.startswith('/' + bucket + '/') and netloc == S3_DOMAIN):
                netloc = bucket + '.' + S3_DOMAIN
                path = path.replace('/' + bucket, '', 1)
            else:
                logging.warning("Got a weird URL in S3 mangling: " + parsed_url)

            # Slide these values back into (a copy of) parsed_url
            new_parsed_url = parsed_url[:]
            new_parsed_url[1] = netloc
            new_parsed_url[2] = path
            return urlparse.urlunparse(new_parsed_url)


DEFAULT_HTTPLIB_CACHE_PATH='/tmp/.cache-for-uid-%d' % os.getuid()
DEFAULT_HTTPLIB_TIMEOUT=20
# We save data inside the httplib cache, but in a hidden directory
OUR_CACHE_DIR = os.path.join(DEFAULT_HTTPLIB_CACHE_PATH,
                             '.cache_downloaded_file')


def http_get(url, _httplib2=None, return_blank_on_failure=True):
    if _httplib2:
        httplib2 = _httplib2
    else:
        import httplib2

    h = httplib2.Http(cache=DEFAULT_HTTPLIB_CACHE_PATH,
                      timeout=DEFAULT_HTTPLIB_TIMEOUT)
    try:
        response, body = h.request(url)
    except AttributeError: # this is the exception httplib2 gives
                           # on socket timeout
        if return_blank_on_failure:
            logging.warn("This URL timed out: " + repr(url))
            return ''
        else:
            raise
    except httplib2.httplib.BadStatusLine, e:
        if not e.args[0] and return_blank_on_failure:
            logging.warn("This URL timed out: %r", url)
            return ''
        else:
            raise

    return body


def cache_downloaded_file(url, http_getter):
    if not os.path.exists(DEFAULT_HTTPLIB_CACHE_PATH):
        os.mkdir(DEFAULT_HTTPLIB_CACHE_PATH, 0700)

    if not os.path.exists(OUR_CACHE_DIR):
        os.mkdir(OUR_CACHE_DIR, 0700)

    response, content = http_getter.request(url, 'GET')
    file_obj = file(os.path.join(OUR_CACHE_DIR,
                                 hashlib.sha1(url).hexdigest()), 'w')
    file_obj.write(content)
    file_obj.close()


def pull_downloaded_file_from_cache(url):
    file_obj = file(os.path.join(OUR_CACHE_DIR,
                                 hashlib.sha1(url).hexdigest()))
    data = file_obj.read()
    file_obj.close()
    return data


def resize_image_returning_list_of_strings(original_image,
                                           THUMB_SIZES):
    ret = []
    # Hackishly copying this constant in for now.
    FORCE_HEIGHT_CROP = 1 # arguments for thumbnail resizing

    for size in THUMB_SIZES:
        if len(size) == 2:
            (width, height), force_height = size, FORCE_HEIGHT_CROP
        else:
            width, height, force_height = size
        resized_image = original_image.copy()
        if resized_image.size != (width, height):
            width_scale = float(resized_image.size[0]) / width
            if force_height:
                height_scale = float(resized_image.size[1]) / height
                if force_height == FORCE_HEIGHT_CROP:
                    # make the resized_image have one side the same as the
                    # thumbnail, and the other bigger so we can crop it
                    if width_scale < height_scale:
                        new_height = int(resized_image.size[1] /
                                         width_scale)
                        new_width = width
                    else:
                        new_width = int(resized_image.size[0] /
                                        height_scale)
                        new_height = height
                else: # FORCE_HEIGHT_PADDING
                    if width_scale < height_scale:
                        new_width = int(resized_image.size[0] /
                                        height_scale)
                        new_height = height
                    else:
                        new_height = int(resized_image.size[1] /
                                         width_scale)
                        new_width = width
                resized_image = resized_image.resize(
                    (new_width, new_height),
                    Image.ANTIALIAS)
                if resized_image.size != (width, height):
                    x = y = 0
                    if force_height == FORCE_HEIGHT_CROP:
                        if resized_image.size[1] > height:
                            y = int((height - resized_image.size[1]) / 2)
                        else:
                            x = int((width - resized_image.size[0]) / 2)
                    else: # FORCE_HEIGHT_PADDING:
                        if resized_image.size[1] == height:
                            x = int((width - resized_image.size[0]) / 2)
                        else:
                            y = int((height - resized_image.size[1]) / 2)
                    new_image = Image.new('RGBA',
                                          (width, height), (0, 0, 0, 0))
                    new_image.paste(resized_image, (x, y))
                    resized_image = new_image
            elif width_scale > 1:
                # resize the width, keep the height aspect ratio the same
                new_height = int(resized_image.size[1] / width_scale)
                resized_image = resized_image.resize((width, new_height),
                                                     Image.ANTIALIAS)
        sio_img = StringIO.StringIO()
        resized_image.save(sio_img, 'png')
        sio_img.seek(0)
        ret.append(
            ((width, height),
             sio_img.read()))
    return ret


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

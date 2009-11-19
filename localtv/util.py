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
import hashlib
import re

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

import vidscraper

from localtv import models
from localtv.templatetags.filters import sanitize


def is_video_type(type):
    application_video_mime_types = [
        "application/ogg",
        "application/x-annodex",
        "application/x-bittorrent",
        "application/x-shockwave-flash"
    ]
    return (type.startswith('video/') or type.startswith('audio/') or
            type in application_video_mime_types)

def get_first_video_enclosure(entry):
    """Find the first video enclosure in a feedparser entry.  Returns the
    enclosure, or None if no video enclosure is found.
    """
    enclosures = entry.get('media_content') or entry.get('enclosures')
    if not enclosures:
        return None
    best_enclosure = None
    for enclosure in enclosures:
        if is_video_type(enclosure.get('type', '')):
            if enclosure.get('isdefault'):
                return enclosure
            elif best_enclosure is None:
                best_enclosure = enclosure
    return best_enclosure

def get_thumbnail_url(entry):
    """Get the URL for a thumbnail from a feedparser entry."""
    # Try the video enclosure
    def _get(d):
        if 'media_thumbnail' in d:
            return d.media_thumbnail[0]['url']
        if 'blip_thumbnail_src' in d and d.blip_thumbnail_src:
            return (u'http://a.images.blip.tv/%s' % (
                d['blip_thumbnail_src'])).encode('utf-8')
        raise KeyError
    video_enclosure = get_first_video_enclosure(entry)
    if video_enclosure is not None:
        try:
            return _get(video_enclosure)
        except KeyError:
            pass
    # Try to get any enclosure thumbnail
    for key in 'media_content', 'enclosures':
        if key in entry:
            for enclosure in entry[key]:
                try:
                    return _get(enclosure)
                except KeyError:
                    pass
    # Try to get the thumbnail for our entry
    try:
        return _get(entry)
    except KeyError:
        pass

    if entry.get('link', '').find(u'youtube.com') != -1:
        if 'content' in entry:
            content = entry.content[0]['value']
        elif 'summary' in entry:
            content = entry.summary
        else:
            return None
        match = re.search(r'<img alt="" src="([^"]+)" />',
                          content)
        if match:
            return match.group(1)

    return None

def get_or_create_tags(tag_list):
    tag_set = set()
    for tag_text in tag_list:
        tags = models.Tag.objects.filter(name=tag_text)
        if not tags:
            tag = models.Tag(name=tag_text)
            tag.save()
        elif tags.count() == 1:
            tag = tags[0]
        else:
            for tag in tags:
                if tag.name == tag:
                    # MySQL doesn't do case-sensitive equals on strings
                    break

        tag_set.add(tag)

    return tag_set


def get_scraped_data(url):
    cache_key = 'vidscraper_data-' + url
    if len(cache_key) >= 250:
        # too long, use the hash
        cache_key = 'vidscraper_data-hash-' + hashlib.sha1(url).hexdigest()
    scraped_data = cache.get(cache_key)

    if not scraped_data:
        # try and scrape the url
        try:
            scraped_data = vidscraper.auto_scrape(url)
        except vidscraper.errors.Error:
            scraped_data = None

        cache.add(cache_key, scraped_data)

    return scraped_data


## ----------------
## Metasearch utils
## ----------------

class MetasearchVideo(object):
    metasearch_vid = True

    def __init__(self, name, description,
                 tags=None, file_url=None,
                 website_url=None, thumbnail_url=None, embed_code='',
                 flash_enclosure_url=None, publish_date=None, id=None,
                 video_service_user=None, video_service_url=None):
        self.name = name.strip()
        self.description = sanitize(description,
                                    extra_filters=['img'])
        if tags:
            self.tags = {
                'objects': {
                    'count': len(tags),
                    'all': [{'name': tag} for tag in tags]
                    }
                }
        else:
            self.tags = {
                'objects':  {
                    'count': 0,
                    'all': []
                    }
                }
        self.file_url = file_url or ''
        self.website_url = website_url or ''
        self.thumbnail_url = thumbnail_url or ''
        self.embed_code = embed_code or ''
        self.flash_enclosure_url = flash_enclosure_url or ''
        self.publish_date = publish_date
        self.video_service_user = video_service_user or ''
        self.video_service_url = video_service_url or ''

        ## NOTE: This ID is only for ordering/hashtable purposes, not
        ## the id this should have once it becomes a model
        self.id = id

    def generate_video_model(self, site, status=models.VIDEO_STATUS_ACTIVE):
        scraped_data = get_scraped_data(self.website_url)
        self.name = scraped_data.get('title', self.name)
        self.description = scraped_data.get('description', self.description)
        self.file_url = scraped_data.get('file_url', self.file_url)
        self.embed_code = scraped_data.get('embed_code', self.embed_code)
        self.flash_enclosure_url = scraped_data.get('flash_enclosure_url',
                                                    self.flash_enclosure_url)
        self.website_url = scraped_data.get('link', self.website_url)

        if scraped_data.get('tags'):
            tags = get_or_create_tags(scraped_data['tags'])
        elif self.tags:
            tags = get_or_create_tags([tag['name'] for tag in
                                       self.tags['objects']['all']])
        else:
            tags = []

        video = models.Video(
            name=self.name,
            site=site,
            description=self.description,
            file_url=self.file_url,
            when_submitted=datetime.datetime.now(),
            when_approved=datetime.datetime.now(),
            status=status,
            website_url=self.website_url,
            thumbnail_url=self.thumbnail_url,
            embed_code=self.embed_code,
            flash_enclosure_url=self.flash_enclosure_url,
            when_published=self.publish_date,
            video_service_user=self.video_service_user,
            video_service_url=self.video_service_url)

        video.save()

        for tag in tags:
            video.tags.add(tag)

        if video.thumbnail_url:
            video.save_thumbnail()

        return video

    @classmethod
    def create_from_vidscraper_dict(cls, vidscraper_dict):
        if 'embed' not in vidscraper_dict and (
            'file_url' not in vidscraper_dict or
            'file_url_flaky' in vidscraper_dict):
            return None

        if 'file_url_flaky' in vidscraper_dict:
            file_url = ''
        else:
            file_url = vidscraper_dict.get('file_url', '')
        return cls(
            name=vidscraper_dict['title'],
            description=vidscraper_dict.get('description'),
            tags=vidscraper_dict.get('tags') or [],
            file_url=file_url,
            website_url=vidscraper_dict.get('link'),
            thumbnail_url=vidscraper_dict.get('thumbnail_url'),
            embed_code=vidscraper_dict.get('embed'),
            flash_enclosure_url=vidscraper_dict.get('flash_enclosure_url'),
            publish_date=vidscraper_dict.get('publish_date'),
            id=vidscraper_dict.get('id'),
            video_service_user=vidscraper_dict.get('user'),
            video_service_url=vidscraper_dict.get('user_url'))

    def when(self):
        return self.publish_date


def metasearch_from_querystring(querystring, order_by='relevant'):
    terms = set(querystring.split())
    exclude_terms = set([
        component for component in terms if component.startswith('-')])
    include_terms = terms.difference(exclude_terms)
    stripped_exclude_terms = [term.lstrip('-') for term in exclude_terms]
    return vidscraper.metasearch.auto_search(
        include_terms, stripped_exclude_terms, order_by)


def strip_existing_metasearchvideos(metasearchvideos, site):
    """
    Remove metasearchvideos that already exist on a specific
    sitelocation.
    """
    filtered_vids = []
    for vid in metasearchvideos:
        if vid.file_url and models.Video.objects.filter(
                site=site, file_url=vid.file_url):
            continue
        elif vid.website_url and models.Video.objects.filter(
                site=site, website_url=vid.website_url):
            continue

        filtered_vids.append(vid)

    return filtered_vids


def sort_header(sort, label, current):
    """
    Generate some metadata for a sortable header.

    @param sort: the sort which this header represents
    @param label: the human-readable label
    @param the current sort

    Returns a dictionary with a link and a CSS class to use for this header,
    based on the scurrent sort.
    """
    if current.endswith(sort):
        # this is the current sort
        css_class = 'sortup'
        if current[0] != '-':
            sort = '-%s' % sort
            css_class = 'sortdown'
    else:
        css_class = ''
    return {
        'sort': sort,
        'link': '?sort=%s' % sort,
        'label': label,
        'class': css_class
        }

def mixed_replace_generator(request, content_generator, bound):
    """
    We take a generator and a boundary string, and yield back content parts for
    the multipart/x-mixed-replace content-type.  The generator should yield
    HTTPResponses.

    The multipart/x-mixed-replace format looks like this:

    --boundary
    Content-type: text/plain

    here's some text, loaded first
    --boundary
    Content-type: text/plain

    <html><body>HTML here!</body></html>
    --boundary--
    """
    yield '--%s' % bound
    try:
        for response in content_generator:
            if response.status_code >= 300 and response.status_code < 400:
                # Some hacks to get redirects to work
                response['Status'] = str(response.status_code)
                response.content = (
                    '<html><head>'
                    '<meta http-equiv="redirect" content="0;url=%(Location)s">'
                    '<script type="text/javascript">'
                    'location.href="%(Location)s";</script>'
                    '</head><body>'
                    'You are being redirected.  If it does not work, click '
                    '<a href="%(Location)s">here</a>.'
                    '</html>' % response)
            yield ''.join((str(response), '\n--', bound))
    except Exception:
        from django.core.urlresolvers import get_resolver
        if settings.DEBUG:
            from django.views import debug
            import sys
            exc_info = sys.exc_info()
            error_view = [debug.technical_500_response,
                          {'exc_type': exc_info[0],
                           'exc_value': exc_info[1],
                           'tb': exc_info[2]}]
        else:
            error_view = get_resolver(None).resolve500()
        error_response = error_view[0](request,
                                       **error_view[1])
        yield ''.join((str(error_response), '\n--', bound))
    yield '--'

class HttpMixedReplaceResponse(HttpResponse):

    def __init__(self, request, generator):
        user_agent = request.META.get('HTTP_USER_AGENT')
        if user_agent is None or 'Safari' in user_agent:
            # Safari's mixed-replace support doesn't seem to work, so just take
            # the last thing from the generator
            response = list(generator)[-1]
            HttpResponse.__init__(self)
            self.__dict__ = response.__dict__
        else:
            self.request = request
            bound = str(id(generator)) + str(id(self))
            HttpResponse.__init__(self,
                                  mixed_replace_generator(request, generator,
                                                          bound),
                                  content_type=('multipart/x-mixed-replace;'
                                             'boundary=\"%s\"' % bound))


    def close(self):
        HttpResponse.close(self)
        if hasattr(self, 'request') and hasattr(self.request, 'session'):
            if self.request.session.modified:
                # Normally this is done in the response middleware, but because
                # the views haven't all been run by the time that middleware is
                # done, we do it again here.

                # TODO(pswartz): This might want to go through all the response
                # middleware instead of just manually doing the session
                # middleware
                self.request.session.save()


class MockQueryset(object):
    """
    Wrap a list of objects in an object which pretends to be a QuerySet.
    """

    def __init__(self, objects):
        self.objects = objects
        self.ordered = True

    def _clone(self):
        return self

    def __len__(self):
        return len(self.objects)

    def __iter__(self):
        return iter(self.objects)

    def __getitem__(self, k):
        if isinstance(k, slice):
            return MockQueryset(self.objects[k])
        return self.objects[k]

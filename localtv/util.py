import datetime

from django.core.cache import cache
from django.db.models import Q
from django.http import HttpResponse

import vidscraper
from vidscraper import metasearch

from localtv import models
from localtv.templatetags.filters import sanitize


VIDEO_EXTENSIONS = [
    '.mov', '.wmv', '.mp4', '.m4v', '.ogg', '.ogv', '.anx',
    '.mpg', '.avi', '.flv', '.mpeg', '.divx', '.xvid', '.rmvb',
    '.mkv', '.m2v', '.ogm']

def is_video_filename(filename):
    """
    Pass a filename to this method and it will return a boolean
    saying if the filename represents a video file.
    """
    filename = filename.lower()
    for ext in VIDEO_EXTENSIONS:
        if filename.endswith(ext):
            return True
    return False


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
        if self.tags:
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

def mixed_replace_generator(content_generator, bound):
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
    --boundary
    """
    yield '--%s' % bound
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
        yield ''.join((str(response), '\r\n--', bound))
    yield '--'

class HttpMixedReplaceResponse(HttpResponse):

    def __init__(self, request, generator):
        user_agent = request.META.get('HTTP_USER_AGENT')
        if user_agent is None or 'Chrome' in user_agent:
            # Chrome's mixed-replace support doesn't seem to work, so just take
            # the last thing from the generator
            response = list(generator)[-1]
            HttpResponse.__init__(self)
            self.__dict__ = response.__dict__
        else:
            self.request = request
            bound = str(id(generator)) + str(id(self))
            HttpResponse.__init__(self,
                                  mixed_replace_generator(generator, bound),
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
        return self.objects[k]

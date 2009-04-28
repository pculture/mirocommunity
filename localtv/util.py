import datetime

from django.core.cache import cache
import vidscraper
from vidscraper import metasearch

from localtv import models


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
    tags = []
    for tag_text in tag_list:
        try:
            tag = models.Tag.objects.get(name=tag_text)
        except models.Tag.DoesNotExist:
            tag = models.Tag(name=tag_text)
            tag.save()

        tags.append(tag)

    return tags


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
                 website_url=None, embed_code='',
                 id=None):
        self.name = name.strip()
        self.description = description
        self.tags = tags or []
        self.file_url = file_url or ''
        self.website_url = website_url or ''
        self.embed_code = embed_code or ''

        ## NOTE: This ID is only for ordering/hashtable purposes, not
        ## the id this should have once it becomes a model
        self.id = id

    def generate_video_model(self, site, save=True):
        if self.tags:
            tags = get_or_create_tags(self.tags)
        else:
            tags = []
        
        video = models.Video(
            name=self.name,
            site=site,
            description=self.description,
            file_url=self.file_url,
            when_submitted=datetime.datetime.now(),
            when_approved=datetime.datetime.now(),
            status=models.VIDEO_STATUS_ACTIVE,
            website_url=self.website_url,
            embed_code=self.embed_code)

        for tag in tags:
            video.tags.add(tag)

        if save:
            video.save()

        return video

    @classmethod
    def create_from_vidscraper_dict(cls, vidscraper_dict):
        return cls(
            name=vidscraper_dict['title'],
            description=vidscraper_dict.get('description'),
            tags=vidscraper_dict.get('tags') or [],
            file_url=vidscraper_dict.get('file_url'),
            website_url=vidscraper_dict.get('link'),
            embed_code=vidscraper_dict.get('embed'),
            id=vidscraper_dict.get('id'))


def metasearch_from_querystring(querystring, order_by='relevant'):
    terms = set(querystring.split())
    exclude_terms = set([
        component for component in terms if component.startswith('-')])
    include_terms = terms.difference(exclude_terms)
    stripped_exclude_terms = [term.lstrip('-') for term in exclude_terms]
    return vidscraper.metasearch.auto_search(
        include_terms, stripped_exclude_terms, order_by)


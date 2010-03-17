import datetime

import vidscraper

from localtv import models
from localtv.templatetags.filters import sanitize

from localtv.util import get_scraped_data, get_or_create_tags

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

        video.try_to_get_file_url_data()
        video.save()
        video.tags = tags
        video.save()
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



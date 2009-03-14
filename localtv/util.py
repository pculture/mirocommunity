from django.core.cache import cache
import vidscraper

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
    

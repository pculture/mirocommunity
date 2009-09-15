from django import template
from django.core.files.storage import default_storage

from localtv.util import MetasearchVideo

register = template.Library()


@register.simple_tag
def get_thumbnail_url(video, width, height):
    if isinstance(video, MetasearchVideo):
        return video.thumbnail_url

    path = video.get_resized_thumb_storage_path(width, height)

    if not default_storage.exists(path):
        return '/images/default_vid.gif'

    return "%s?%i" % (default_storage.url(path), default_storage.size(path))

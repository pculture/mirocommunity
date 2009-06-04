from django import template
from django.core.files.storage import default_storage

from localtv.util import MetasearchVideo

register = template.Library()


@register.simple_tag
def get_thumbnail_url(video, width, height):
    if isinstance(video, MetasearchVideo):
        return video.thumbnail_url

    return default_storage.url(
        video.get_resized_thumb_storage_path(width, height))

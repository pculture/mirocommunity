from django import template
from django.core.files.storage import default_storage


register = template.Library()


@register.simple_tag
def get_thumbnail_url(video, width, height):
    return default_storage.url(
        video.get_resized_thumb_storage_path(width, height))

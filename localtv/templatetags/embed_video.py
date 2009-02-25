import mimetypes

from django import template

register = template.Library()

DEFAULT_WIDTH = 480
DEFAULT_HEIGHT= 360

EMBED_DEFAULT_TEMPLATE = "localtv/embed_video/default.html"
EMBED_QUICKTIME_TEMPLATE = "localtv/embed_video/quicktime.html"
EMBED_FLASH_TEMPLATE = "localtv/embed_video/flash.html"


def quicktime_embed(file_url):
    embed_template = template.loader.get_template(EMBED_QUICKTIME_TEMPLATE)
    return embed_template.render(
        template.Context(
            {'file_url': file_url,
             'width': DEFAULT_WIDTH,
             'height': DEFAULT_HEIGHT + 15}))

def flash_embed(file_url):
    embed_template = template.loader.get_template(EMBED_FLASH_TEMPLATE)
    return embed_template.render(
        template.Context(
            {'file_url': file_url,
             'width': DEFAULT_WIDTH,
             'height': DEFAULT_HEIGHT + 36}))

def default_embed(file_url):
    embed_template = template.loader.get_template(EMBED_DEFAULT_TEMPLATE)
    return embed_template.render(
        template.Context(
            {'file_url': file_url,
             'width': DEFAULT_WIDTH,
             'height': DEFAULT_HEIGHT}))


EMBED_MAPPING = {
    'video/mp4': quicktime_embed,
    'video/quicktime': quicktime_embed,
    'audio/mpeg': quicktime_embed,
    'video/x-m4v': quicktime_embed,
    'video/mpeg': quicktime_embed,
    'video/m4v': quicktime_embed,
    'video/mov': quicktime_embed,
    'audio/x-m4a': quicktime_embed,
    'audio/mp4': quicktime_embed,
    'video/x-mp4': quicktime_embed,
    'audio/mp3': quicktime_embed,
    'application/x-shockwave-flash': flash_embed,
    'video/x-flv': flash_embed,
    'video/flv': flash_embed,
}


@register.simple_tag
def embed_video(video):
    mime_type = mimetypes.guess_type(video.file_url)
    func = EMBED_MAPPING.get(
        mimetypes.guess_type(video.file_url), default_embed)
    return func(video.file_url)

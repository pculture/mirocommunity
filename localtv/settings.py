from django.conf import settings

__all__ = ('USE_HAYSTACK', 'API_KEYS')

USE_HAYSTACK = getattr(settings, 'LOCALTV_USE_HAYSTACK', True)

_keymap = {
    'vimeo_key': 'VIMEO_API_KEY',
    'vimeo_secret': 'VIMEO_API_SECRET',
    'ustream_key': 'USTREAM_API_KEY',
    'youtube_key': 'YOUTUBE_API_KEY',
}

API_KEYS = dict((k, getattr(settings, v))
                for k, v in _keymap.iteritems()
                if getattr(settings, v, None) is not None)

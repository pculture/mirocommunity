from django.conf import settings

__all__ = ('POPULAR_QUERY_TIMEOUT', 'SHOW_ADMIN_DASHBOARD',
           'SHOW_ADMIN_ACCOUNT_LEVEL', 'USE_HAYSTACK', 'API_KEYS')

#: The amount of time that the "popular videos" query is considered valid.
#: Default: 2 hours. (2 * 60 * 60 seconds)
POPULAR_QUERY_TIMEOUT = getattr(settings, 'LOCALTV_POPULAR_QUERY_TIMEOUT',
                                2 * 60 * 60)
SHOW_ADMIN_DASHBOARD = getattr(settings, 'LOCALTV_SHOW_ADMIN_DASHBOARD', True)
SHOW_ADMIN_ACCOUNT_LEVEL = getattr(settings, 'LOCALTV_SHOW_ADMIN_ACCOUNT_LEVEL',
                                   True)
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

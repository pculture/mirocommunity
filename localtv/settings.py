from django.conf import settings

#: The amount of time that the "popular videos" query is considered valid.
#: Default: 2 hours. (2 * 60 * 60 seconds)
POPULAR_QUERY_TIMEOUT =  getattr(settings, 'LOCALTV_POPULAR_QUERY_TIMEOUT',
                                 2 * 60 * 60)
SHOW_ADMIN_DASHBOARD = getattr(settings, 'LOCALTV_SHOW_ADMIN_DASHBOARD', True)
SHOW_ADMIN_ACCOUNT_LEVEL = getattr(settings, 'LOCALTV_SHOW_ADMIN_ACCOUNT_LEVEL',
                                   True)
USE_HAYSTACK = getattr(settings, 'LOCALTV_USE_HAYSTACK', True)

API_KEYS = {
    'vimeo_key': getattr(settings, 'VIMEO_API_KEY', None),
    'vimeo_secret': getattr(settings, 'VIMEO_API_SECRET', None),
    'ustream_key': getattr(settings, 'USTREAM_API_KEY', None)
}

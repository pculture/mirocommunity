import os

from django.conf import settings

from localtv.models import SiteSettings, Video, Category
from localtv.settings import ENABLE_CHANGE_STAMPS


BROWSE_NAVIGATION_MODULES = [
    'localtv/_modules/browse/videos.html',
    'localtv/_modules/browse/categories.html',
]


def localtv(request):
    site_settings = SiteSettings.objects.get_current()

    display_submit_button = site_settings.display_submit_button
    if display_submit_button:
        if request.user.is_anonymous() and \
                site_settings.submission_requires_login:
            display_submit_button = False
    else:
        if request.user_is_admin():
            display_submit_button = True

    if ENABLE_CHANGE_STAMPS:
        try:
            cache_invalidator = os.stat(
                os.path.join(settings.MEDIA_ROOT,
                             '.video-published-stamp')).st_mtime
        except OSError:
            cache_invalidator = None
    else:
        try:
            cache_invalidator = str(Video.objects.order_by(
                    '-when_modified').values_list(
                    'when_modified', flat=True)[0])
        except IndexError:
            cache_invalidator = None

    return  {
        'mc_version': '1.2',
        'site_settings': site_settings,
        # Backwards-compatible for custom themes.
        'sitelocation': site_settings,
        'user_is_admin': request.user_is_admin(),
        'categories':  Category.objects._mptt_filter(site=site_settings.site,
                                                     parent__isnull=True),
        'cache_invalidator': cache_invalidator,

        'display_submit_button': display_submit_button,

        'settings': settings,

        'VIDEO_STATUS_UNAPPROVED': Video.UNAPPROVED,
        'VIDEO_STATUS_ACTIVE': Video.ACTIVE,
        'VIDEO_STATUS_REJECTED': Video.REJECTED}


def browse_modules(request):
    """
    Returns a list of templates that will be used to build the "browse" menu
    in the navigation.

    """
    return {
        'browse_modules': BROWSE_NAVIGATION_MODULES
    }

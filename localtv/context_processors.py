from django.conf import settings

from localtv.models import SiteSettings, Video, Category
from localtv.admin.urls import admin_riff


BROWSE_NAVIGATION_MODULES = [
    'localtv/_modules/browse/videos.html',
    'localtv/_modules/browse/categories.html',
]


def localtv(request):
    site_settings = SiteSettings.objects.get_current()

    display_submit_button = (site_settings.display_submit_button or
                             request.user_is_admin())

    safe_settings = ('FACEBOOK_APP_ID', 'LOGIN_URL', 'LOGOUT_URL',
                     'GOOGLE_ANALYTICS_UA', 'GOOGLE_ANALYTICS_DOMAIN',
                     'MEDIA_URL', 'RECAPTCHA_PUBLIC_KEY')
    settings_context = dict((setting, getattr(settings, setting, ''))
                            for setting in safe_settings)

    new_context = settings_context.copy()

    # LOGIN_URL and LOGOUT_URL should be handled via {% url %} tags.
    del new_context['LOGIN_URL']
    del new_context['LOGOUT_URL']

    # MEDIA_URL shouldn't be necessary - ImageFile.url works better.
    del new_context['MEDIA_URL']

    new_context.update({
        'site_settings': site_settings,
        'categories': Category.objects._mptt_filter(site=site_settings.site,
                                                    parent__isnull=True),

        # Deprecated/backwards-compatibility.
        'settings': settings_context,
        'sitelocation': site_settings,
        'user_is_admin': request.user_is_admin(),
        'display_submit_button': display_submit_button,
        'VIDEO_STATUS_UNAPPROVED': Video.UNAPPROVED,
        'VIDEO_STATUS_ACTIVE': Video.ACTIVE,
        'VIDEO_STATUS_REJECTED': Video.REJECTED,
        'base_riff': admin_riff,
    })

    return new_context


def browse_modules(request):
    """
    Returns a list of templates that will be used to build the "browse" menu
    in the navigation.

    """
    return {
        'browse_modules': BROWSE_NAVIGATION_MODULES
    }

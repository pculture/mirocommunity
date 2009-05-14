from django.contrib.sites.models import Site

from localtv import models


def context_processor(request):
    sitelocation = models.SiteLocation.objects.get(
            site=Site.objects.get_current())

    openid_localtv = request.session.get('openid_localtv')

    return  {
        'VIDEO_STATUS_UNAPPROVED': models.VIDEO_STATUS_UNAPPROVED,
        'VIDEO_STATUS_ACTIVE': models.VIDEO_STATUS_ACTIVE,
        'VIDEO_STATUS_REJECTED': models.VIDEO_STATUS_REJECTED,

        'FEED_STATUS_UNAPPROVED': models.FEED_STATUS_UNAPPROVED,
        'FEED_STATUS_ACTIVE': models.FEED_STATUS_ACTIVE,
        'FEED_STATUS_REJECTED': models.FEED_STATUS_REJECTED,
        
        'SITE_STATUS_DISABLED': models.SITE_STATUS_DISABLED,
        'SITE_STATUS_ACTIVE': models.SITE_STATUS_ACTIVE,

        'OPENID_STATUS_DISABLED': models.OPENID_STATUS_DISABLED,
        'OPENID_STATUS_ACTIVE': models.OPENID_STATUS_ACTIVE,

        'sitelocation': sitelocation,
        'openid_localtv': openid_localtv}

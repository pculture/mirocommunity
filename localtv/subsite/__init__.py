from django.conf import settings
from django.contrib.sites.models import Site

from localtv import models


def context_processor(request):
    sitelocation = models.SiteLocation.objects.get(
            site=Site.objects.get_current())

    display_submit_button = sitelocation.display_submit_button
    if display_submit_button:
        if request.user.is_authenticated() and sitelocation.submission_requires_login:
            display_submit_button = False
    else:
        if sitelocation.user_is_admin(request.user):
            display_submit_button = True

    return  {
        'sitelocation': sitelocation,
        'request': request,
        'user_is_admin': sitelocation.user_is_admin(request.user),

        'display_submit_button': display_submit_button,

        'settings': settings}

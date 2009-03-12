import urllib

from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from localtv import models

def get_sitelocation(view_func):
    """
    Push the current sitelocation as part of the view's arguments
    """
    def new_view_func(request, *args, **kwargs):
        sitelocation = models.SiteLocation.objects.get(
            site=Site.objects.get_current())
        return view_func(request, sitelocation=sitelocation, *args, **kwargs)

    # make decorator safe
    new_view_func.__name__ = view_func.__name__
    new_view_func.__dict__ = view_func.__dict__
    new_view_func.__doc__ = view_func.__doc__

    return new_view_func


def require_active_openid(view_func):
    def new_view_func(request, *args, **kwargs):
        openid_localtv = request.session.get('openid_localtv')
        if (not openid_localtv
               or not openid_localtv.status == models.OPENID_STATUS_ACTIVE):
            # redirect here
            redirect_url = reverse('localtv_openid_start')
            redirect_url += '?' + urllib.urlencode(
                {'next': request.META['PATH_INFO']})
            return HttpResponseRedirect(redirect_url)
        else:
            return view_func(request, *args, **kwargs)
            
    # make decorator safe
    new_view_func.__name__ = view_func.__name__
    new_view_func.__dict__ = view_func.__dict__
    new_view_func.__doc__ = view_func.__doc__

    return new_view_func

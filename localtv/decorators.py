import urllib

from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from localtv import models

def _make_safe(decorator, original):
    """
    Copy the function data from the old function to the decorator.
    """
    decorator.__name__ = original.__name__
    decorator.__dict__ = original.__dict__
    decorator.__doc__ = original.__doc__
    return decorator

def get_sitelocation(view_func):
    """
    Push the current sitelocation as part of the view's arguments
    """
    def new_view_func(request, *args, **kwargs):
        sitelocation = models.SiteLocation.objects.get(
            site=Site.objects.get_current())
        return view_func(request, sitelocation=sitelocation, *args, **kwargs)

    return _make_safe(new_view_func, view_func)


def request_passes_test(test_func):
    def decorate(view_func):
        def new_view_func(request, *args, **kwargs):
            if not test_func(request):
                # redirect here
                redirect_url = reverse('localtv_openid_start')
                redirect_url += '?' + urllib.urlencode(
                    {'next': request.META['PATH_INFO']})
                return HttpResponseRedirect(redirect_url)
            else:
                return view_func(request, *args, **kwargs)

        return _make_safe(new_view_func, view_func)

    return decorate


def _check_active_openid(request):
    openid_localtv = request.session.get('openid_localtv')
    return openid_localtv and \
        openid_localtv.status == models.OPENID_STATUS_ACTIVE

require_active_openid = request_passes_test(_check_active_openid)

def _check_site_admin(request):
    openid_localtv = request.session.get('openid_localtv')
    return openid_localtv and openid_localtv.admin_for_current_site()

require_site_admin = request_passes_test(_check_site_admin)

def referrer_redirect(view_func):
    def new_view_func(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        if response.status_code != 200:
            return response # don't break other redirects
        requested_with = request.META.get('HTTP_X_REQUESTED_WITH')
        if requested_with == 'XMLHttpRequest':
            return response # don't do redirects for AJAX calls
        referer = request.META.get('HTTP_REFERER')
        if referer is not None:
            return HttpResponseRedirect(referer)
        else:
            return response

    return _make_safe(new_view_func, view_func)

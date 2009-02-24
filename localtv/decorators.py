from django.contrib.sites.models import Site

from localtv.models import SiteLocation

def get_sitelocation(view_func):
    """
    Push the current sitelocation as part of the view's arguments
    """
    def new_view_func(request, *args, **kwargs):
        sitelocation = SiteLocation.objects.get(
            site=Site.objects.get_current())
        return view_func(request, sitelocation=sitelocation, *args, **kwargs)

    # make decorator safe
    new_view_func.__name__ = view_func.__name__
    new_view_func.__dict__ = view_func.__dict__
    new_view_func.__doc__ = view_func.__doc__

    return new_view_func

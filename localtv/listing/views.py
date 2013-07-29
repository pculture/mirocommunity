from django.contrib.sites.models import Site
from django.views.generic import ListView


class SiteListView(ListView):
    """
    Filters the ordinary queryset according to the current site.

    """
    def get_queryset(self):
        return super(SiteListView, self).get_queryset().filter(
                                site=Site.objects.get_current())

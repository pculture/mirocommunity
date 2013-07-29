from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView

from localtv.search.views import SortFilterView


urlpatterns = patterns(
    'localtv.listing.views',
    url(r'^new/$',
        SortFilterView.as_view(
            template_name='localtv/video/new.html',
        ),
        name='localtv_list_new'),
    url(r'^popular/$',
        SortFilterView.as_view(
            template_name='localtv/video/popular.html',
            sort='popular',
        ),
        name='localtv_list_popular'),
    url(r'^featured/$',
        SortFilterView.as_view(
            template_name='localtv/video/featured.html',
            sort='featured',
            filter_name='featured',
            filter_kwarg='value',
        ),
        {'value': True},
        name='localtv_list_featured'),
    url(r'^tag/(?P<name>.+)/$',
        SortFilterView.as_view(
            template_name='localtv/video/tag.html',
            filter_name='tag',
            filter_kwarg='name'
        ),
        name='localtv_list_tag'),
    url(r'^feed/(?P<pk>\d+)/?$',
        SortFilterView.as_view(
            template_name='localtv/video/feed.html',
            filter_name='feed'
        ),
        name='localtv_list_feed'),

    # Compat.
    url(r'^this-week/$',
        RedirectView.as_view(permanent=False,
                             url=reverse_lazy('localtv_list_new')),
        name='localtv_list_this_week'),
)

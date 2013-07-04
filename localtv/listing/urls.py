import datetime

from django.conf.urls.defaults import patterns, url

from localtv.listing.views import CompatibleListingView


urlpatterns = patterns(
    'localtv.listing.views',
    url(r'^new/$',
        CompatibleListingView.as_view(
            old_template_name='localtv/video_listing_new.html',
            template_name='localtv/video/new.html',
        ),
        name='localtv_list_new'),
    url(r'^this-week/$',
        CompatibleListingView.as_view(
            old_template_name='localtv/video_listing_this_week.html',
            template_name='localtv/video/this-week.html',
            approved_since=datetime.timedelta(days=7),
            sort='approved',
        ),
        name='localtv_list_this_week'),
    url(r'^popular/$',
        CompatibleListingView.as_view(
            old_template_name='localtv/video_listing_popular.html',
            template_name='localtv/video/popular.html',
            sort='popular',
        ),
        name='localtv_list_popular'),
    url(r'^featured/$',
        CompatibleListingView.as_view(
            old_template_name='localtv/video_listing_featured.html',
            template_name='localtv/video/featured.html',
            sort='featured',
            filter_name='featured',
            filter_kwarg='value',
        ),
        {'value': True},
        name='localtv_list_featured'),
    url(r'^tag/(?P<name>.+)/$',
        CompatibleListingView.as_view(
            old_template_name='localtv/video_listing_tag.html',
            template_name='localtv/video/tag.html',
            filter_name='tag',
            filter_kwarg='name'
        ),
        name='localtv_list_tag'),
    url(r'^feed/(?P<pk>\d+)/?$',
        CompatibleListingView.as_view(
            old_template_name='localtv/video_listing_feed.html',
            template_name='localtv/video/feed.html',
            filter_name='feed'
        ),
        name='localtv_list_feed')
)

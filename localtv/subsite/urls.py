from django.conf.urls.defaults import patterns, include
from django.conf import settings

urlpatterns = patterns(
    'localtv.subsite.views',
    (r'^$', 'subsite_index', {}, 'localtv_subsite_index'),
    (r'^about/$', 'about', {}, 'localtv_about'),
    (r'^search/$', 'video_search', {}, 'localtv_subsite_search'),
    (r'^category/$', 'category', {}, 'localtv_subsite_category_index'),
    (r'^category/([-\w]+)$', 'category', {}, 'localtv_subsite_category'),
    (r'^video/(?P<video_id>[0-9]+)/$', 'view_video',
     {}, 'localtv_view_video'))

urlpatterns += patterns(
    '',
    (r'^openid/', include('localtv.openid.urls')),
    (r'^admin/', include('localtv.subsite.admin.urls')),
    (r'^submit_video/', include('localtv.subsite.submit_video.urls')),
    (r'^listing/', include('localtv.subsite.listing.urls')),
    (r'^feeds/', include('localtv.subsite.feeds.urls')))

if settings.DEBUG:
    # show the thumbnails/logo etc, without relying on Apache
    urlpatterns += patterns('',
                            (r'^localtv/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'localtv'}),
                            )

from django.conf.urls.defaults import patterns, include

from localtv.openid.urls import urlpatterns as openid_urlpatterns

urlpatterns = patterns(
    'localtv.subsite.views',
    (r'^$', 'subsite_index', {}, 'localtv_subsite_index'),
    (r'^video/(?P<video_id>[0-9]+)/$', 'view_video',
     {}, 'localtv_view_video'))

urlpatterns += patterns(
    '',
    (r'^openid/', include('localtv.openid.urls')),
    (r'^submit_video/', include('localtv.subsite.submit_video.urls')))


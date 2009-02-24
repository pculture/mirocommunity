from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    'localtv.views',
    (r'^$', 'subsite_index', {}, 'localtv_subsite_index'),
    (r'^video/(?P<video_id>[0-9]+)/$', 'view_video',
     {}, 'localtv_subsite_view_video'))

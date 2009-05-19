from django.conf.urls.defaults import patterns, include

urlpatterns = patterns(
    'localtv.subsite.feeds.views',
    (r'^new/$', 'new', {}, 'localtv_subsite_feeds_new'),
    (r'^featured/$', 'featured', {}, 'localtv_subsite_feeds_featured'),
    (r'^popular/$', 'popular', {}, 'localtv_subsite_feeds_popular'))

from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    'localtv.subsite.listing.views',
    (r'^$', 'index', {}, 'localtv_subsite_list_index'),
    (r'^new/$', 'new_videos', {}, 'localtv_subsite_list_new'),
    (r'^popular/$', 'popular_videos', {}, 'localtv_subsite_list_popular'),
    (r'^featured/$', 'featured_videos', {}, 'localtv_subsite_list_featured'),
    (r'^tag/(.*)$', 'tag_videos', {}, 'localtv_subsite_list_tag'),
    (r'^feed/(\d*)$', 'feed_videos', {}, 'localtv_subsite_list_feed'))

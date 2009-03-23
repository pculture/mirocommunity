from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    'localtv.subsite.listing.views',
    (r'^$', 'index', {}, 'localtv_subsite_list_index'),
    (r'^new/$', 'new_videos', {}, 'localtv_subsite_list_new'))

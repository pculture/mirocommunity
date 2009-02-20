from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    'localtv.views',
    (r'^$', 'subsite_index', {}, 'localtv_subsite_index'))

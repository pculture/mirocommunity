from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    'localtv.subsite.admin.edit_attributes.feed_views',
    (r'^feed/(?P<id>[0-9]+)/name/$', 'edit_name',
     {}, 'localtv_admin_feed_edit_title'),
    (r'^feed/(?P<id>[0-9]+)/auto_categories/$', 'edit_auto_categories',
     {}, 'localtv_admin_feed_edit_auto_categories'),
    (r'^feed/(?P<id>[0-9]+)/auto_authors/$', 'edit_auto_authors',
     {}, 'localtv_admin_feed_edit_auto_authors'))

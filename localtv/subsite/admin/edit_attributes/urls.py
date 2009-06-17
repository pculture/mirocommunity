from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    'localtv.subsite.admin.edit_attributes.feed_views',
    (r'^feed/name/$', 'edit_name',
     {}, 'localtv_admin_feed_edit_title'),
    (r'^feed/auto_categories/$', 'edit_auto_categories',
     {}, 'localtv_admin_feed_edit_auto_categories'),
    (r'^feed/auto_authors/$', 'edit_auto_authors',
     {}, 'localtv_admin_feed_edit_auto_authors'))

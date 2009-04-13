from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    'localtv.subsite.admin.views',
    (r'^test_table/$', 'test_table', {}, 'localtv_admin_test_table'),
    (r'^approve_reject/$', 'approve_reject',
     {}, 'localtv_admin_approve_reject'),
    (r'^preview_video/$', 'preview_video',
     {}, 'localtv_admin_preview_video'),
    (r'^actions/reject_video/$', 'reject_video',
     {}, 'localtv_admin_reject_video'),
    (r'^actions/approve_video/$', 'approve_video',
     {}, 'localtv_admin_approve_video'),
    (r'^feeds/$', 'feeds_page',
     {}, 'localtv_admin_feed_page'))


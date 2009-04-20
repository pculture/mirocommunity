from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    'localtv.subsite.admin.approve_reject_views',
    (r'^approve_reject/$', 'approve_reject',
     {}, 'localtv_admin_approve_reject'),
    (r'^preview_video/$', 'preview_video',
     {}, 'localtv_admin_preview_video'),
    (r'^actions/reject_video/$', 'reject_video',
     {}, 'localtv_admin_reject_video'),
    (r'^actions/approve_video/$', 'approve_video',
     {}, 'localtv_admin_approve_video'))


urlpatterns += patterns(
    'localtv.subsite.admin.feed_views',
    (r'^feeds/$', 'feeds_page',
     {}, 'localtv_admin_feed_page'),
    (r'^feeds/stop_watching/$', 'feed_stop_watching',
     {}, 'localtv_admin_feed_stop_watching'),
    (r'^feeds/auto_approve/$', 'feed_auto_approve',
     {}, 'localtv_admin_feed_auto_approve'))


urlpatterns += patterns(
    'localtv.subsite.admin.livesearch_views',
    (r'^livesearch/$', 'livesearch_page',
     {}, 'localtv_admin_livesearch_page'),
    (r'^livesearch/approve/$', 'approve',
     {}, 'localtv_admin_livesearch_approve'))

from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    'localtv.subsite.admin.approve_reject_views',
    (r'^approve_reject/$', 'approve_reject',
     {}, 'localtv_admin_approve_reject'),
    (r'^preview_video/$', 'preview_video',
     {}, 'localtv_admin_preview_video'),
    (r'^actions/reject_video/$', 'reject_video',
     {}, 'localtv_admin_reject_video_action'),
    (r'^actions/approve_video/$', 'approve_video',
     {}, 'localtv_admin_approve_video_action'))


urlpatterns += patterns(
    'localtv.subsite.admin.feed_views',
    (r'^feeds/$', 'feeds_page',
     {}, 'localtv_admin_feed_page'),
    (r'^feeds/add_feed/$', 'add_feed',
     {}, 'localtv_admin_feed_add'),
    (r'^feeds/stop_watching/$', 'feed_stop_watching',
     {}, 'localtv_admin_feed_stop_watching'),
    (r'^feeds/auto_approve/$', 'feed_auto_approve',
     {}, 'localtv_admin_feed_auto_approve'))


urlpatterns += patterns(
    'localtv.subsite.admin.livesearch_views',
    (r'^livesearch/$', 'livesearch_page',
     {}, 'localtv_admin_livesearch_page'),
    (r'^livesearch/approve/$', 'approve',
     {}, 'localtv_admin_livesearch_approve'),
    (r'^livesearch/display/$', 'display',
     {}, 'localtv_admin_livesearch_display'),
    (r'^livesearch/save_search/$', 'create_saved_search',
     {}, 'localtv_admin_livesearch_save_search'),
    (r'^livesearch/remove/$', 'remove_saved_search',
     {}, 'localtv_admin_livesearch_remove'))


urlpatterns += patterns(
    'localtv.subsite.admin.edit_video_views',
    (r'^edit_video/$', 'edit_video',
     {}, 'localtv_admin_edit_video'),
    (r'^reject_video/$', 'reject_video',
     {}, 'localtv_admin_reject_video'),
    (r'^feature_video/$', 'feature_video',
     {}, 'localtv_admin_feature_video'))

urlpatterns += patterns(
    'localtv.subsite.admin.design_views',
    (r'^design/$', 'edit_design',
     {}, 'localtv_admin_edit_design'))

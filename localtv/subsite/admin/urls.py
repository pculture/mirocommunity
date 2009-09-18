from django.conf.urls.defaults import patterns, include

urlpatterns = patterns(
    'localtv.subsite.admin.approve_reject_views',
    (r'^approve_reject/$', 'approve_reject',
     {}, 'localtv_admin_approve_reject'),
    (r'^preview_video/$', 'preview_video',
     {}, 'localtv_admin_preview_video'),
    (r'^actions/reject_video/$', 'reject_video',
     {}, 'localtv_admin_reject_video'),
    (r'^actions/approve_video/$', 'approve_video',
     {}, 'localtv_admin_approve_video'),
    (r'^actions/feature_video/$', 'feature_video',
     {}, 'localtv_admin_feature_video'),
    (r'^actions/unfeature_video/$', 'unfeature_video',
     {}, 'localtv_admin_unfeature_video'),
    (r'^actions/reject_all/$', 'reject_all',
     {}, 'localtv_admin_reject_all'),
    (r'^actions/approve_all/$', 'approve_all',
     {}, 'localtv_admin_approve_all'),
    (r'^actions/clear_all/$', 'clear_all',
     {}, 'localtv_admin_clear_all'),
    )


urlpatterns += patterns(
    'localtv.subsite.admin.sources_views',
    (r'^manage/$', 'manage_sources',
     {}, 'localtv_admin_manage_page'))

urlpatterns += patterns(
    'localtv.subsite.admin.feed_views',
    (r'^manage/feed/add$', 'add_feed',
     {}, 'localtv_admin_feed_add'),
    (r'^manage/feed/remove$', 'feed_stop_watching',
     {}, 'localtv_admin_feed_remove'),
    (r'^manage/feed/auto_approve$', 'feed_auto_approve',
     {}, 'localtv_admin_feed_auto_approve'))

urlpatterns += patterns(
    'localtv.subsite.admin.livesearch_views',
    (r'^manage/search/add$', 'create_saved_search',
     {}, 'localtv_admin_search_add'),
    (r'^manage/search/remove$', 'remove_saved_search',
     {}, 'localtv_admin_search_remove'),
    (r'^add/approve/$', 'approve',
     {}, 'localtv_admin_search_video_approve'),
    (r'^add/display/$', 'display',
     {}, 'localtv_admin_search_video_display'))

urlpatterns += patterns(
    'localtv.subsite.admin.edit_video_views',
    (r'^edit_video/$', 'edit_video',
     {}, 'localtv_admin_edit_video'))

urlpatterns += patterns(
    'localtv.subsite.admin.design_views',
    (r'^design/$', 'edit_design',
     {}, 'localtv_admin_edit_design'))

urlpatterns += patterns(
    'localtv.subsite.admin.category_views',
    (r'^categories/$', 'categories',
     {}, 'localtv_admin_categories'))

urlpatterns += patterns(
    'localtv.subsite.admin.bulk_edit_views',
    (r'^bulk_edit/$', 'bulk_edit', {},
     'localtv_admin_bulk_edit'))

urlpatterns += patterns(
    '',
    (r'^edit_attributes/',
     include('localtv.subsite.admin.edit_attributes.urls')))

urlpatterns += patterns(
    'localtv.subsite.admin.user_views',
    (r'^users/$', 'users',
     {}, 'localtv_admin_users'))

urlpatterns += patterns(
    'localtv.subsite.admin.comment_views',
    (r'^comments/spam/(\d+)/$', 'comments_spam', {}, 'comments-spam'))

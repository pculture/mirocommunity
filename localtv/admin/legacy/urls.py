from django.conf.urls import patterns, url

urlpatterns = patterns(
    'localtv.admin.legacy.views',
    (r'^$', 'index', {}, 'localtv_admin_index'),
    (r'^hide_get_started$', 'hide_get_started', {}, 'localtv_admin_hide_get_started'))

urlpatterns += patterns(
    'localtv.admin.legacy.approve_reject_views',
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
    'localtv.admin.legacy.sources_views',
    url(r'^manage/$', 'manage_sources',
        name='localtv_admin_manage_page'),
    url(r'^manage/search/(?P<pk>\d+)$', 'edit_search',
        name='localtv_admin_search_edit'),
    url(r'^manage/search/(?P<pk>\d+)/delete$', 'delete_search',
        name='localtv_admin_search_delete'))

urlpatterns += patterns('localtv.admin.legacy.feed_views',
    url(r'^manage/feed/add$', 'add_feed',
        name='localtv_admin_feed_add'),
    url(r'^manage/feed/auto_approve/(?P<pk>\d+)$', 'feed_auto_approve',
        name='localtv_admin_feed_auto_approve'),
    url(r'^manage/feed/(?P<pk>\d+)$', 'edit_feed',
        name='localtv_admin_feed_edit'),
    url(r'^manage/feed/(?P<pk>\d+)/delete$', 'delete_feed',
        name='localtv_admin_feed_delete'))

urlpatterns += patterns(
    'localtv.admin.legacy.livesearch.views',
    (r'^manage/search/$', 'livesearch',
     {}, 'localtv_admin_search'),
    (r'^manage/search/add$', 'create_saved_search',
     {}, 'localtv_admin_search_add'),
    (r'^manage/search/auto_approve/(?P<pk>\d+)$', 'search_auto_approve',
     {}, 'localtv_admin_search_auto_approve'),
    (r'^add/approve/$', 'approve',
     {}, 'localtv_admin_search_video_approve'),
    (r'^add/display/$', 'display',
     {}, 'localtv_admin_search_video_display'))

urlpatterns += patterns(
    'localtv.admin.legacy.edit_video_views',
    (r'^edit_video/$', 'edit_video',
     {}, 'localtv_admin_edit_video'))

urlpatterns += patterns(
    'localtv.admin.legacy.design_views',
    (r'^settings/$', 'edit_settings',
     {}, 'localtv_admin_settings'),
    (r'^settings/widget/$', 'widget_settings',
     {}, 'localtv_admin_widget_settings'))

urlpatterns += patterns(
    'localtv.admin.legacy.category_views',
    (r'^categories/$', 'categories',
     {}, 'localtv_admin_categories'),
)

urlpatterns += patterns(
    'localtv.admin.legacy.bulk_edit_views',
    (r'^bulk_edit/$', 'bulk_edit', {},
     'localtv_admin_bulk_edit'))

urlpatterns += patterns(
    'localtv.admin.legacy.user_views',
    (r'^users/$', 'users',
     {}, 'localtv_admin_users'))

urlpatterns += patterns(
    'localtv.admin.legacy.comment_views',
    (r'^comments/spam/(\d+)/$', 'comments_spam', {}, 'comments-spam'),
    (r'^comments/spamed/$', 'spam_done', {}, 'comments-spam-done'))

urlpatterns += patterns(
    'localtv.admin.legacy.upload_views',
    url(r'^themes/$', 'index',
        name='uploadtemplate-index'),
    url(r'^themes/add/$', 'create',
        name='uploadtemplate-create'),
    url(r'^themes/(?P<pk>\d+)/edit$', 'update',
        name='uploadtemplate-update'),
    url(r'^themes/(\d+)/delete$', 'delete',
        name='uploadtemplate-delete'),
    url(r'^themes/download/(\d+)$', 'download',
        name='uploadtemplate-download'),
    url(r'^themes/unset_default$', 'unset_default',
        name='uploadtemplate-unset_default'),
    url(r'^themes/set_default/(\d+)$', 'set_default',
        name='uploadtemplate-set_default'))

urlpatterns += patterns(
    'localtv.admin.legacy.flatpages_views',
    (r'^flatpages/$', 'index', {}, 'localtv_admin_flatpages'))

urlpatterns += patterns(
    'localtv.admin.legacy.feeds',
    (r'^feeds/(\S+)/unapproved$', 'unapproved', {},
     'localtv_admin_feed_unapproved'),
    (r'^feeds/(\S+)/unapproved_user$', 'unapproved_user', {},
     'localtv_admin_feed_unapproved_user'))


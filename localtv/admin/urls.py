# Copyright 2009 - Participatory Culture Foundation
# 
# This file is part of Miro Community.
# 
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
# 
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    'localtv.admin.views',
    (r'^$', 'index', {}, 'localtv_admin_index'),
    (r'^hide_get_started$', 'hide_get_started', {}, 'localtv_admin_hide_get_started'))

urlpatterns += patterns(
    'localtv.admin.approve_reject_views',
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
    'localtv.admin.sources_views',
    (r'^manage/$', 'manage_sources',
     {}, 'localtv_admin_manage_page'))

urlpatterns += patterns(
    'localtv.admin.feed_views',
    (r'^manage/feed/add$', 'add_feed',
     {}, 'localtv_admin_feed_add'),
    (r'^manage/feed/add/(\d+)$', 'add_feed_done',
     {}, 'localtv_admin_feed_add_done'),
    (r'^manage/feed/auto_approve/(\d+)$', 'feed_auto_approve',
     {}, 'localtv_admin_feed_auto_approve'))

urlpatterns += patterns(
    'localtv.admin.livesearch_views',
    (r'^manage/search/$', 'livesearch',
     {}, 'localtv_admin_search'),
    (r'^manage/search/add$', 'create_saved_search',
     {}, 'localtv_admin_search_add'),
    (r'^manage/search/auto_approve/(\d+)$', 'search_auto_approve',
     {}, 'localtv_admin_search_auto_approve'),
    (r'^add/approve/$', 'approve',
     {}, 'localtv_admin_search_video_approve'),
    (r'^add/display/$', 'display',
     {}, 'localtv_admin_search_video_display'))

urlpatterns += patterns(
    'localtv.admin.edit_video_views',
    (r'^edit_video/$', 'edit_video',
     {}, 'localtv_admin_edit_video'))

urlpatterns += patterns(
    'localtv.admin.design_views',
    (r'^settings/$', 'edit_settings',
     {}, 'localtv_admin_settings'),
    (r'^settings/widget/$', 'widget_settings',
     {}, 'localtv_admin_widget_settings'))

urlpatterns += patterns(
    'localtv.admin.category_views',
    (r'^categories/$', 'categories',
     {}, 'localtv_admin_categories'))

urlpatterns += patterns(
    'localtv.admin.bulk_edit_views',
    (r'^bulk_edit/$', 'bulk_edit', {},
     'localtv_admin_bulk_edit'))

urlpatterns += patterns(
    'localtv.admin.user_views',
    (r'^users/$', 'users',
     {}, 'localtv_admin_users'))

urlpatterns += patterns(
    'localtv.admin.comment_views',
    (r'^comments/spam/(\d+)/$', 'comments_spam', {}, 'comments-spam'),
    (r'^comments/spamed/$', 'spam_done', {}, 'comments-spam-done'))

urlpatterns += patterns(
    'localtv.admin.upload_views',
    (r'^themes/$', 'index', {}, 'uploadtemplate-index'),
    (r'^themes/delete/(\d+)$', 'delete', {}, 'uploadtemplate-delete'),
    (r'^themes/download/(\d+)$', 'download', {}, 'uploadtemplate-download'),
    (r'^themes/set_default/(\d+)$', 'set_default', {},
     'uploadtemplate-set_default'))

urlpatterns += patterns(
    'localtv.admin.flatpages_views',
    (r'^flatpages/$', 'index', {}, 'localtv_admin_flatpages'))

urlpatterns += patterns(
    'localtv.admin.feeds',
    (r'^feeds/(\S+)/unapproved$', 'unapproved', {},
     'localtv_admin_feed_unapproved'),
    (r'^feeds/(\S+)/unapproved_user$', 'unapproved_user', {},
     'localtv_admin_feed_unapproved_user'))

urlpatterns += patterns('localtv.admin.tiers',
    (r'^upgrade/$',             'upgrade', {}, 'localtv_admin_tier'),
    (r'^paypal_return/(?P<payment_secret>.+)/(?P<target_tier_name>[a-z_]+?)/$',             'paypal_return', {}, 'localtv_admin_paypal_return'),
    (r'^begin_free_trial/(?P<payment_secret>.+?)/$',             'begin_free_trial', {}, 'localtv_admin_begin_free_trial'),
    (r'^downgrade_confirm/$',             'downgrade_confirm', {}, 'localtv_admin_downgrade_confirm'),
    (r'^confirmed_change_tier/$',             'confirmed_change_tier', {}, 'localtv_admin_confirmed_change_tier'),
    (r'^ipn_endpoint/(?P<payment_secret>.+?)/$',             'ipn_endpoint', {}, 'localtv_admin_ipn_endpoint'),
)

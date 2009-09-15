# Miro Community
# Copyright 2009 - Participatory Culture Foundation
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
    'localtv.subsite.admin.manage_views',
    (r'^manage/$', 'manage_sources',
     {}, 'localtv_admin_manage_page'),
    (r'^manage/stop_watching/$', 'feed_stop_watching',
     {}, 'localtv_admin_feed_stop_watching'),
    (r'^manage/auto_approve/$', 'feed_auto_approve',
     {}, 'localtv_admin_feed_auto_approve'),
    (r'^manage/remove/$', 'remove_saved_search',
     {}, 'localtv_admin_livesearch_remove'))


urlpatterns += patterns(
    'localtv.subsite.admin.add_views',
    (r'^add/$', 'add_source',
     {}, 'localtv_admin_add_page'),
    (r'^add/feed/$', 'add_feed',
     {}, 'localtv_admin_feed_add'),
    (r'^add/search/$', 'create_saved_search',
     {}, 'localtv_admin_search_add'),
    (r'^add/approve/$', 'approve',
     {}, 'localtv_admin_livesearch_approve'),
    (r'^add/display/$', 'display',
     {}, 'localtv_admin_livesearch_display'))


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
    'localtv.subsite.admin.author_views',
    (r'^authors/$', 'authors',
     {}, 'localtv_admin_authors'),
    (r'^authors/delete$', 'delete',
     {}, 'localtv_admin_authors_delete'))

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

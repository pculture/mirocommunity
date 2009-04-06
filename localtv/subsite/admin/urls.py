from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    'localtv.subsite.admin.views',
    (r'^test_table/$', 'test_table', {}, 'localtv_admin_test_table'),
    (r'^approve_reject/$', 'approve_reject',
     {}, 'localtv_admin_approve_reject'))


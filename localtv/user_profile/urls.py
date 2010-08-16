from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    'localtv.user_profile.views',
    (r'^$', 'profile', {}, 'localtv_user_profile'),
    (r'^notifications/$', 'notifications', {}, 'localtv_user_notifications'))

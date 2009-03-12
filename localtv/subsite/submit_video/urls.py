from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    'localtv.subsite.submit_video.views',
    (r'^$', 'submit_video', {}, 'localtv_submit_video'),
    (r'^preview/$', 'preview_before_submit', {}, 'localtv_submit_video_preview'))

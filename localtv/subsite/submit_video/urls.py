from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    'localtv.subsite.submit_video.views',
    (r'^$', 'submit_video', {}, 'localtv_submit_video'),
    (r'^scraped/$', 'scraped_submit_video',
     {}, 'localtv_submit_scraped_video'),
    (r'^embed/$', 'embedrequest_submit_video',
     {}, 'localtv_submit_embedrequest_video'),
    (r'^directlink/$', 'directlink_submit_video',
     {}, 'localtv_submit_directlink_video'),
    (r'^thanks/$', 'submit_thanks', {}, 'localtv_submit_thanks'))

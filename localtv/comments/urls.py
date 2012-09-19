from django.conf.urls import patterns, url, include


urlpatterns = patterns('',
    url(r'^post/$', 'localtv.comments.views.post_comment', name='comments-post-comment'),
    url(r'^', include('django.contrib.comments.urls'))
)

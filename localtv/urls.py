from django.conf.urls.defaults import patterns, include, url
from django.contrib.auth.models import User
from django.views.generic import ListView

from localtv.api.v1 import api as api_v1
from localtv.listing.views import SiteListView
from localtv.models import Category
from localtv.search.views import SortFilterView
from localtv.views import IndexView, VideoView, can_submit, SubmitView


# "Base" patterns
urlpatterns = patterns(
    'localtv.views',
    url(r'^$', IndexView.as_view(), name='localtv_index'),
    url(r'^about/$', 'about', name='localtv_about'),
    url(r'^share/(\d+)/(\d+)', 'share_email', name='email-share'),
    url(r'^video/(?P<video_id>[0-9]+)(?:/(?P<slug>[\w~-]+))?/?$',
        VideoView.as_view(),
        name='localtv_view_video'),
    url(r'^submit/$',
        can_submit(SubmitView.as_view()),
        name='localtv_submit_video'),
    url(r'^api/', include(api_v1.urls)))

# Listing patterns
# This has to be importable for now because of a hack in the view_video view
# which imports this view to check whether the referer was a category page.
category_videos = SortFilterView.as_view(
    template_name='localtv/category.html',
    filter_name='category',
    filter_kwarg='slug'
)
urlpatterns += patterns(
    'localtv.listing.views',
    url(r'^search/$',
        SortFilterView.as_view(
            template_name='localtv/video/search.html',
        ),
        name='localtv_search'),
    url(r'^category/$', SiteListView.as_view(
                        template_name='localtv/categories.html',
                        queryset=Category.objects.filter(level=0),
                        paginate_by=15
                    ), name='localtv_category_index'),
    url(r'^category/(?P<slug>[-\w]+)/$', category_videos,
                    name='localtv_category'),
    url(r'^author/$', ListView.as_view(
                        template_name='localtv/author_list.html',
                        model=User,
                        context_object_name='authors'
                    ), name='localtv_author_index'),
    url(r'^author/(?P<pk>\d+)/$', SortFilterView.as_view(
                        template_name='localtv/author.html',
                        filter_name='author'
                    ), name='localtv_author'))

# Comments patterns
urlpatterns += patterns(
    'localtv.comments.views',
    url(r'^comments/post/$', 'post_comment', name='comments-post-comment'),
    url(r'^comments/moderation-queue$', 'moderation_queue', {},
                    'comments-moderation-queue'),
    url(r'^comments/moderation-queue/undo$', 'undo', {},
                    'comments-moderation-undo'),
    url(r'^comments/', include('django.contrib.comments.urls')))

# Various inclusions
urlpatterns += patterns(
    '',
    url(r'^thumbs/', include('daguerre.urls')),
    url(r'^admin/', include('localtv.admin.urls')),
    url(r'^admin/', include('registration.backends.default.urls')),
    url(r'^admin/', include('social_auth.urls')),
    url(r'^listing/', include('localtv.listing.urls')),
    url(r'^feeds/', include('localtv.feeds.urls')),
    url(r'^goodies/', include('localtv.goodies.urls')),
    url(r'^share/', include('email_share.urls')),
    url(r'^playlists/', include('localtv.playlists.urls')))

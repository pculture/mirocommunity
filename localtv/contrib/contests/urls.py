from django.conf.urls.defaults import patterns, url

from localtv.contrib.contests.models import Contest
from localtv.contrib.contests.views import (ContestDetailView,
                                            ContestListingView,
                                            ContestAdminListView,
                                            ContestAdminCreateView,
                                            ContestAdminUpdateView,
                                            ContestAdminDeleteView)
from localtv.submit_video.forms import (ScrapedSubmitVideoForm,
                                                   EmbedSubmitVideoForm,
                                                   DirectLinkSubmitVideoForm)
from localtv.contrib.contests.submit_views import (can_submit_video,
                                                   SubmitURLView,
                                                   SubmitVideoView,
                                                   submit_thanks)
from localtv.decorators import require_site_admin
from localtv.listing.views import SiteListView


urlpatterns = patterns('localtv.contrib.voting.views',
    url(r'^contests/$',
        SiteListView.as_view(model=Contest,
                             template_name='contests/list.html'),
        name='contests_contest_list'),
    url(r'^contests/(?P<pk>[0-9]+)(?:/(?P<slug>[\w-]+))?/?$',
    	ContestDetailView.as_view(),
        name='contests_contest_detail'),
    url(r'^contests/(?P<pk>[0-9]+)(?:/(?P<slug>[\w-]+))?/videos/?$',
    	ContestListingView.as_view(),
        name='contests_contest_listing'),
    url(r'^admin/contests/?$',
        require_site_admin(ContestAdminListView.as_view()),
    	name='localtv_admin_contests'),
    url(r'^admin/contests/add/?$',
        require_site_admin(ContestAdminCreateView.as_view()),
        name='localtv_admin_contests_create'),
    url(r'^admin/contests/edit/(?P<pk>[\d]+)/?$',
        require_site_admin(ContestAdminUpdateView.as_view()),
        name='localtv_admin_contests_update'),
    url(r'^admin/contests/delete/(?P<pk>[\d]+)/?$',
        require_site_admin(ContestAdminDeleteView.as_view()),
        name='localtv_admin_contests_delete'),
)

urlpatterns += patterns('localtv.contrib.voting.submit_views',
    url(r'^contests/(?P<pk>[0-9]+)(?:/(?P<slug>[\w-]+))?/submit/?$',
        can_submit_video(SubmitURLView.as_view()),
    	name='localtv_contests_submit_video'),
    url(r'^contests/(?P<pk>[0-9]+)(?:/(?P<slug>[\w-]+))?/submit/scraped/$',
        can_submit_video(SubmitVideoView.as_view(
            form_class=ScrapedSubmitVideoForm,
            template_name='contests/submit_video/scraped.html',
            form_fields=('tags', 'contact', 'notes'),
        )),
        name='localtv_contests_submit_scraped_video'),
    url(r'^contests/(?P<pk>[0-9]+)(?:/(?P<slug>[\w-]+))?/submit/embed/$',
        can_submit_video(SubmitVideoView.as_view(
            form_class=EmbedSubmitVideoForm,
            template_name='contests/submit_video/embed.html',
            form_fields=('tags', 'contact', 'notes', 'name', 'description',
                         'thumbnail_url', 'embed_code'),
        )),
        name='localtv_contests_submit_embedrequest_video'),
    url(r'^contests/(?P<pk>[0-9]+)(?:/(?P<slug>[\w-]+))?/submit/directlink/$',
        can_submit_video(SubmitVideoView.as_view(
            form_class=DirectLinkSubmitVideoForm,
            template_name='contests/submit_video/direct.html',
            form_fields=('tags', 'contact', 'notes', 'name', 'description',
                         'thumbnail_url', 'website_url'),
        )),
        name='localtv_contests_submit_directlink_video'),
    url(r'^contests/(?P<pk>[0-9]+)(?:/(?P<slug>[\w-]+))?/submit/thanks/(?P<video_id>\d+)?$',
        submit_thanks,
        name='localtv_contests_submit_thanks')
)


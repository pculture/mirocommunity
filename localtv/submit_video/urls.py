# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2009, 2010, 2011, 2012 Participatory Culture Foundation
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

from django.conf.urls.defaults import patterns, url
from django.core.urlresolvers import reverse_lazy

from localtv.submit_video.forms import (ScrapedSubmitVideoForm,
                                        EmbedSubmitVideoForm,
                                        DirectLinkSubmitVideoForm)
from localtv.submit_video.views import (can_submit_video,
                                        SubmitURLView,
                                        SubmitVideoView,
                                        submit_thanks)

urlpatterns = patterns('',
    url(r'^$',
        can_submit_video(SubmitURLView.as_view(
            scraped_url=reverse_lazy('localtv_submit_scraped_video'),
            direct_url=reverse_lazy('localtv_submit_directlink_video'),
            embed_url=reverse_lazy('localtv_submit_embedrequest_video'),
        )),
    	name='localtv_submit_video'),
    url(r'^scraped/$',
        can_submit_video(SubmitVideoView.as_view(
            submit_video_url=reverse_lazy('localtv_submit_video'),
            thanks_url_name='localtv_submit_thanks',
            form_class=ScrapedSubmitVideoForm,
            template_name='localtv/submit_video/scraped.html',
            form_fields=('tags', 'contact', 'notes'),
        )),
        name='localtv_submit_scraped_video'),
    url(r'^embed/$',
        can_submit_video(SubmitVideoView.as_view(
            submit_video_url=reverse_lazy('localtv_submit_video'),
            thanks_url_name='localtv_submit_thanks',
            form_class=EmbedSubmitVideoForm,
            template_name='localtv/submit_video/embed.html',
            form_fields=('tags', 'contact', 'notes', 'name', 'description',
                         'thumbnail_url', 'embed_code'),
        )),
        name='localtv_submit_embedrequest_video'),
    url(r'^directlink/$',
        can_submit_video(SubmitVideoView.as_view(
            submit_video_url=reverse_lazy('localtv_submit_video'),
            thanks_url_name='localtv_submit_thanks',
            form_class=DirectLinkSubmitVideoForm,
            template_name='localtv/submit_video/direct.html',
            form_fields=('tags', 'contact', 'notes', 'name', 'description',
                         'thumbnail_url', 'website_url'),
        )),
        name='localtv_submit_directlink_video'),
    url(r'^thanks/(?P<video_id>\d+)?$',
        submit_thanks,
        name='localtv_submit_thanks')
)

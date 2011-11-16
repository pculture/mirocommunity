# Copyright 2010 - Participatory Culture Foundation
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

from django.conf.urls.defaults import patterns, url, include
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _

from localtv.admin.base import MiroCommunityAdminSection, CRUDSection, registry
from localtv.admin.videos.forms import VideoForm, CategoryForm, PlaylistForm
from localtv.models import Video, Category
from localtv.playlists.models import Playlist


class VideoCRUDSection(CRUDSection):
    create_form_class = VideoForm
    update_form_class = VideoForm

    def get_queryset(self):
        return Video.objects.filter(site=Site.objects.get_current())


class CategoryCRUDSection(CRUDSection):
    create_form_class = CategoryForm
    update_form_class = CategoryForm

    def get_queryset(self):
        return Category.objects.filter(site=Site.objects.get_current())


class PlaylistCRUDSection(CRUDSection):
    create_form_class = PlaylistForm
    update_form_class = PlaylistForm
    model = Playlist


class VideoSection(MiroCommunityAdminSection):
    url_prefix = 'videos'
    navigation_text = _('Videos')

    def __init__(self):
        self.subsections = [
            VideoCRUDSection(),
            CategoryCRUDSection(),
            PlaylistCRUDSection(),
        ]

    @property
    def urlpatterns(self):
        urlpatterns = patterns('')

        for section in self.subsections:
            urlpatterns += patterns('',
                url(r'^%s/' % section.url_prefix, include(section.urlpatterns))
            )
        return urlpatterns

    @property
    def pages(self):
        pages = ()
        for section in self.subsections:
            pages += section.pages
        return pages


registry.register(VideoSection)
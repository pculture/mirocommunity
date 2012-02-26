# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2010, 2011, 2012 Participatory Culture Foundation
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

from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _

from localtv.admin.base import MiroCommunityAdminSection, CRUDSection, registry
from localtv.admin.videos.forms import (VideoForm, CreateVideoForm,
                                        CategoryForm)
from localtv.admin.videos.views import VideoCreateView
from localtv.models import Video, Category


class VideoCRUDSection(CRUDSection):
    create_form_class = CreateVideoForm
    update_form_class = VideoForm
    create_view_class = VideoCreateView
    site_admin_required = False

    def get_queryset(self):
        return Video.objects.filter(site=Site.objects.get_current())


class CategoryCRUDSection(CRUDSection):
    update_form_class = CategoryForm

    def get_queryset(self):
        return Category.objects.filter(site=Site.objects.get_current())


class VideoSection(MiroCommunityAdminSection):
    url_prefix = 'videos'
    navigation_text = _('Videos')
    subsection_classes = [VideoCRUDSection, CategoryCRUDSection]

    @property
    def root_url_name(self):
        return self.subsections[0].root_url_name


registry.register(VideoSection)
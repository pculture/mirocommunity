# Copyright 2009 - Participatory Culture Foundation
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

from django import template
from django.core.files.storage import default_storage

from localtv.admin.util import MetasearchVideo

register = template.Library()


@register.simple_tag
def get_thumbnail_url(video, width, height):
    if isinstance(video, MetasearchVideo):
        return video.thumbnail_url

    thumbnails = [source for source in [video, video.feed, video.search]
                  if source is not None]
    for thumbnail in thumbnails:
        if thumbnail.has_thumbnail:
            break

    if not thumbnail.has_thumbnail:
        return '/images/default_vid.gif'

    return default_storage.url(
        thumbnail.get_resized_thumb_storage_path(width, height))

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

class ThumbnailNode(template.Node):
    def __init__(self, video, size, as_varname=None):
        self.video = video
        self.size = size
        self.as_varname = as_varname

    def render(self, context):
        video = self.video.resolve(context)
        thumbnail_url = self.get_thumbnail_url(video)
        if self.as_varname is not None:
            context[self.as_varname] = thumbnail_url
            return ''
        else:
            return thumbnail_url

    def get_thumbnail_url(self, video):
        if isinstance(video, MetasearchVideo):
            return video.thumbnail_url

        thumbnail = None

        if video.has_thumbnail:
            thumbnail = video
        elif video.feed and video.feed.has_thumbnail:
            thumbnail = video.feed
        elif video.search and video.search.has_thumbnail:
            thumbnail = video.search

        if not thumbnail:
            return '/images/default_vid.gif'

        url = default_storage.url(
            thumbnail.get_resized_thumb_storage_path(*self.size))

        if thumbnail._meta.get_latest_by:
            key = hex(hash(getattr(thumbnail,
                                   thumbnail._meta.get_latest_by)))[-8:]
            return '%s?%s' % (url, key)
        else:
            return url

@register.tag('get_thumbnail_url')
def get_thumbnail_url(parser, token):
    tokens = token.split_contents()
    if len(tokens) not in (4, 6):
        raise template.TemplateSyntaxError(
            '%r tag requires 4 or 6 arguments' % (tokens[0],))
    try:
        width = int(tokens[2])
        height = int(tokens[3])
    except ValueError:
        raise template.TemplateSyntaxError(
            'Third and forth arguments in %r tag must be integers' % (
                tokens[0],))
    video = template.Variable(tokens[1])
    if len(tokens) == 6: # get_thumbnail_url video width height as variable
        if tokens[4] != 'as':
            raise template.TemplateSyntaxError(
                "Fifth argument in %r tag must be 'as'" % tokens[0])
        return ThumbnailNode(video, (width, height), tokens[5])
    else:
        return ThumbnailNode(video, (width, height))


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
from django.contrib.sites.models import Site

register = template.Library()

class ThumbnailNode(template.Node):
    def __init__(self, video, size, as_varname=None, absolute=False):
        self.video = video
        self.size = size
        self.as_varname = as_varname
        self.absolute = absolute

    def render(self, context):
        video = self.video.resolve(context)
        thumbnail_url = self.get_thumbnail_url(video, context)
        if self.as_varname is not None:
            context[self.as_varname] = thumbnail_url
            return ''
        else:
            return thumbnail_url

    def get_thumbnail_url(self, video, context):
        if video.pk is None:
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
            url = '%s?%s' % (url, key)
        if not self.absolute or url.startswith(('http://', 'https://')):
            # full URL, return it
            return url
        else:
            # add the domain
            if 'request' in context:
                request = context['request']
                scheme = 'https' if request.is_secure() else 'http'
            else:
                scheme = 'http'
            domain = Site.objects.get_current().domain
            return '%s://%s%s' % (scheme, domain, url)
@register.tag('get_thumbnail_url')
def get_thumbnail_url(parser, token):
    tokens = token.split_contents()
    if len(tokens) not in (4, 5, 6, 7):
        raise template.TemplateSyntaxError(
            '%r tag requires 4, 5, 6 or 7 arguments' % (tokens[0],))
    absolute = (tokens[1] == 'absolute')
    if absolute:
        if len(tokens) not in (5, 7):
            raise template.TemplateSyntaxError(
                '%r absolute tag requires 5 or 7 arguments' % (tokens[0],))
    elif len(tokens) not in (4, 6):
            raise template.TemplateSyntaxError(
                '%r tag requires 4 or 6 arguments' % (tokens[0],))        
    try:
        width = int(tokens[2 + absolute])
        height = int(tokens[3 + absolute])
    except ValueError:
        raise template.TemplateSyntaxError(
            'Third and forth arguments in %r tag must be integers' % (
                tokens[0],))
    video = template.Variable(tokens[1 + absolute])
    if len(tokens) == (6 + absolute): # get_thumbnail_url video width height as
                                    # variable
        if tokens[4 + absolute] != 'as':
            raise template.TemplateSyntaxError(
                "Fifth argument in %r tag must be 'as'" % tokens[0])
        return ThumbnailNode(video, (width, height), tokens[5 + absolute],
                             absolute=absolute)
    else:
        return ThumbnailNode(video, (width, height),
                             absolute=absolute)


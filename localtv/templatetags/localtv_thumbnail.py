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

from django import template
from django.conf import settings
from django.core.files.storage import default_storage
from django.contrib.sites.models import Site

from daguerre.models import Image
from daguerre.templatetags.daguerre import ImageResizeNode, ImageProxy

register = template.Library()

class ThumbnailNode(ImageResizeNode):
    """
    Essentially an implementation of daguerre's ImageResizeNode with a
    different interface, to maintain backwards compatibility with old
    localtv_thumbnail template tags.
    
    """
    
    def __init__(self, video, size, as_varname=None, absolute=False):
        self.asvar = as_varname
        self.absolute = absolute # ???
        self.video = video
        self.width, self.height = size
    
    def render(self, context):
        storage_path = self.video.resolve(context).get_original_thumb_storage_path()
        kwargs = {'width': self.width, 'height': self.height, 'method': 'fill'}
        image = Image.objects.for_storage_path(storage_path)
        
        proxy = ImageProxy(image, kwargs)
        
        if self.asvar is not None:
            context[self.asvar] = proxy
            return ''
        return proxy


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


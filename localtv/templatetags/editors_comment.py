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

from django import template
from django.contrib import comments
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site

register = template.Library()

class EditorsCommentNode(template.Node):

    def __init__(self, obj, as_varname):
        self.obj = obj
        self.as_varname = as_varname

    def render(self, context):
        obj = self.obj.resolve(context)
        content_type = ContentType.objects.get_for_model(obj)
        try:
            comment = comments.get_model().objects.get(
                site=Site.objects.get_current(),
                content_type=content_type,
                object_pk=unicode(obj.pk),
                flags__flag='editors comment')
        except comments.get_model().DoesNotExist:
            pass
        else:
            context[self.as_varname] = comment
        return ''

@register.tag('get_editors_comment')
def get_editors_comment(parser, token):
    tokens = token.split_contents()
    if len(tokens) != 5:
        raise template.TemplateSyntaxError(
            "%r tag requires 5 arguments" % (tokens[0],))
    if tokens[1] != 'for':
        raise template.TemplateSyntaxError(
            "Second argument in %r tag must be 'for'" % tokens[0])
    if tokens[3] != 'as':
        raise template.TemplateSyntaxError(
            "Fourth argument in %r tag must be 'as'" % tokens[0])
    return EditorsCommentNode(template.Variable(tokens[2]), tokens[4])

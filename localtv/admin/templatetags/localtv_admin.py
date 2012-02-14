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

from django import template
from django.core.urlresolvers import reverse

from localtv.admin import registry, user_registry


register = template.Library()


class RegistryNode(template.Node):
    registry = registry

    def __init__(self, as_var):
        self.as_var = as_var
    
    def render(self, context):
        request = context.get('request', None)
        if request is not None:
            context[self.as_var] = self.registry._registry.values()
        return ''


class UserRegistryNode(RegistryNode):
    registry = user_registry


@register.tag
def get_admin_sections(parser, token):
    """
    Sets a list of current admin sections to a variable in the context.

    Example::

        {% get_admin_sections as admin_sections %}

    """
    bits = token.split_contents()
    tag_name = bits[0]

    if len(bits) != 3:
        raise template.TemplateSyntaxError(
                        "`%s` tag expects exactly three arguments" % tag_name)
    
    if bits[1] != "as":
        raise template.TemplateSyntaxError(
                        "Second argument to `%s` tag must be 'as'" % tag_name)

    return RegistryNode(bits[2])


@register.tag
def get_user_sections(parser, token):
    """
    Sets a list of current user sections for the admin to a variable in the
    context.

    Example::

        {% get_user_sections as user_sections %}
    """
    bits = token.split_contents()
    tag_name = bits[0]

    if len(bits) != 3:
        raise template.TemplateSyntaxError(
                        "`%s` tag expects exactly three arguments" % tag_name)
    
    if bits[1] != "as":
        raise template.TemplateSyntaxError(
                        "Second argument to `%s` tag must be 'as'" % tag_name)

    return UserRegistryNode(bits[2])


@register.filter
def is_active(section, request):
    return section.is_active(request)

@register.filter
def is_available(section, request):
    return section.is_available(request)

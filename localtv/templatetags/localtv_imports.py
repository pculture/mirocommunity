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
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist


register = template.Library()


class SourceImportInfoNode(template.Node):
    def __init__(self, source_var, as_var):
        self.source_var = source_var
        self.as_var = as_var

    def render(self, context):
        source = self.source_var.resolve(context)
        try:
            source_import = source.imports.latest()
        except ObjectDoesNotExist:
            source_import = None

        if source_import is not None:
            errors = source_import.errors.exclude(traceback=''
                             ).values_list('message', flat=True)
        else:
            errors = None

        context[self.as_var] = {
            'import': source_import,
            'errors': errors
        }
        return ''


@register.tag
def get_source_import_info(parser, token):
    """
    Fetches information about the most recent import for a source and stores
    it as a context variable. The variable has the following keys:

    * ``import``: The import instance.
    * ``errors``: A flat value queryset of all messages from import errors which
                  were caused by exceptions.

    Syntax::

        {% get_source_import_info <source> as <varname> %}

    """
    bits = token.split_contents()
    tag_name = bits[0]

    if len(bits) != 4:
        raise template.TemplateSyntaxError("%s template tag requires exactly "
                                           "three arguments.")

    if bits[2] != "as":
        raise template.TemplateSyntaxError("%s template tag's second argument "
                                           "must be 'as'.")

    return SourceImportInfoNode(source_var=parser.compile_filter(bits[1]),
                                as_var=bits[3])

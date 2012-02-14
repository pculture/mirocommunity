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
register = template.Library()

### Based on http://djangosnippets.org/snippets/1243/
def do_generate_modified_query_string(parser, token):
   try:
       tag_name, key, value = token.split_contents()
   except ValueError:
       return GetStringNode()

   if not (key[0] == key[-1] and key[0] in ('"', "'")):
       raise template.TemplateSyntaxError, "%r tag's argument should be in quotes" % tag_name

   return GetStringNode(key[1:-1], value)

class GetStringNode(template.Node):
   def __init__(self, key=None, value=None):
       self.key = key
       if value:
           self.value = template.Variable(value)

   def render(self, context):
       get = context.get('request').GET.copy()

       if self.key:
           actual_value = self.value.resolve(context)
           get.__setitem__(self.key, actual_value)

       return get.urlencode()

register.tag('generate_modified_query_string', do_generate_modified_query_string)



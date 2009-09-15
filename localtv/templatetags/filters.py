# Miro Community
# Copyright 2009 - Participatory Culture Foundation
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
from BeautifulSoup import BeautifulSoup, Comment
from django.template import Library
from django.utils.safestring import mark_safe

register = Library()

def simpletimesince(value, arg=None):
    """Formats a date as the time since that date (i.e. "4 days, 6 hours")."""
    from django.utils.timesince import timesince
    if not value:
        return u''
    try:
        if arg:
            return timesince(value, arg)
        return timesince(value).split(', ')[0]
    except (ValueError, TypeError):
        return u''

def sanitize(value):
    """
    Sanitize the given HTML.

    Based on code from:
    * http://www.djangosnippets.org/snippets/1655/
    * http://www.djangosnippets.org/snippets/205/
    """
    if value is None:
        return u''
    
    js_regex = re.compile(r'[\s]*(&#x.{1,7})?'.join(list('javascript')),
                          re.IGNORECASE)
    allowed_tags = 'p i strong em b u a h1 h2 h3 h4 h5 h6 pre br img'.split()
    allowed_attributes = 'href src'.split()

    soup = BeautifulSoup(value)
    for comment in soup.findAll(text=lambda text: isinstance(text, Comment)):
        # remove comments
        comment.extract()

    for tag in soup.findAll(True):
        if tag.name not in allowed_tags:
            tag.hidden = True
        else:
            tag.attrs = [(attr, js_regex.sub('', val))
                         for attr, val in tag.attrs
                         if attr in allowed_attributes]

    return mark_safe(soup.renderContents().decode('utf8'))

register.filter(simpletimesince)
register.filter(sanitize)

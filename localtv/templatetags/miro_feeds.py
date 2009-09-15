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

from django import template
from django.core.urlresolvers import reverse


register = template.Library()

MIRO_SUBSCRIBE_BASE = 'http://subscribe.getmiro.com/'
#'http://subscribe.getmiro.com/?url1=http%3A//podcast.cnbc.com/mmpodcast/suzeormanshow.xml&trackback1=https%3A//www.miroguide.com/feeds/10063/subscribe-hit

def subscribify_url(url):
    pass


@register.simple_tag
def reversible_miro_subscribe_feed(reversible_url):
    actual_url = reverse(reversible_url)

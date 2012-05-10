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

"""
Creates the default SiteSettings object.
"""
import datetime

from django.contrib.auth.models import User


TWO_MONTHS = datetime.timedelta(days=62)


def site_too_old():
    if User.objects.order_by('-last_login').values_list(
        'last_login', flat=True)[0] + TWO_MONTHS < datetime.datetime.now():
        return True
    else:
        return False

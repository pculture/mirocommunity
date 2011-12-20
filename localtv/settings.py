# Copyright 2011 - Participatory Culture Foundation
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

from django.conf import settings

#: The amount of time that the "popular videos" query is considered valid.
#: Default: 2 hours. (2 * 60 * 60 seconds)
POPULAR_QUERY_TIMEOUT =  getattr(settings, 'LOCALTV_POPULAR_QUERY_TIMEOUT',
                                 2 * 60 * 60)
ENABLE_ORIGINAL_VIDEO = not getattr(settings,
                                    'LOCALTV_DONT_LOG_REMOTE_VIDEO_HISTORY',
                                    None)
ENABLE_CHANGE_STAMPS = getattr(settings, 'LOCALTV_ENABLE_CHANGE_STAMPS', False)
VOTING_ENABLED = 'voting' in settings.INSTALLED_APPS
USE_ZENDESK = getattr(settings, 'LOCALTV_USE_ZENDESK', False)
DISABLE_TIERS_ENFORCEMENT = getattr(settings,
                                    'LOCALTV_DISABLE_TIERS_ENFORCEMENT', False)
SHOW_ADMIN_DASHBOARD = getattr(settings, 'LOCALTV_SHOW_ADMIN_DASHBOARD', True)
SHOW_ADMIN_ACCOUNT_LEVEL = getattr(settings, 'LOCALTV_SHOW_ADMIN_ACCOUNT_LEVEL',
                                   True)


def voting_enabled():
    """
    Returns a bool() indicating whether voting should be enabled on this site.
    """
    return VOTING_ENABLED

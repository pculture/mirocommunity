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

# Trigger some adjustments to core registries.
from localtv import context_processors
from localtv.contrib.contests.api import v1
from localtv.views import VideoView


context_processors.BROWSE_NAVIGATION_MODULES.append(
									'localtv/_modules/browse/contests.html')
VideoView.sidebar_modules.insert(0, 'localtv/_modules/contests.html')

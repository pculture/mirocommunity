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

import math
from datetime import datetime, timedelta

from django.contrib import comments
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from localtv.models import Video, SiteLocation
from localtv.tiers import current_videos_that_count_toward_limit


class DashboardView(TemplateView):
    template_name = 'localtv/admin/dashboard.html'

    def get_context_data(self):
        sitelocation = SiteLocation.objects.get_current()
        total_count = current_videos_that_count_toward_limit().count()
        percent_videos_used = math.floor((100.0 * total_count) /
                                        sitelocation.get_tier().videos_limit())
        videos_this_week_count = Video.objects.filter(
                                    status=Video.ACTIVE,
                                    when_approved__gt=(
                                        datetime.utcnow() - timedelta(days=7)
                                    )
                                ).count()
        return {
            'total_count': total_count,
            'percent_videos_used': percent_videos_used,
            'unreviewed_count': Video.objects.filter(
                                    status=Video.UNAPPROVED,
                                    site=sitelocation.site
                                ).count(),
            'videos_this_week_count': videos_this_week_count,
            'comment_count': comments.get_model().objects.filter(
                                    is_public=False, is_removed=False).count()
        }
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

from localtv.admin.views import MiroCommunityAdminCreateView
from localtv.tasks import CELERY_USING


class SourceCreateView(MiroCommunityAdminCreateView):
    """
    View for creating sources, which immediately queues a task for importing
    the source.

    """
    #: The task for importing the source. Default: None.
    import_task = None

    def get_form_kwargs(self):
        kwargs = super(SourceCreateView, self).get_form_kwargs()
        kwargs.update({
            'user': self.request.user
        })
        return kwargs

    def form_valid(self, form):
        response = super(SourceCreateView, self).form_valid(form)
        self.import_task.delay(self.object.pk, using=CELERY_USING)
        return response

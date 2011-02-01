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

from django.core.management.base import BaseCommand

import localtv.tiers
import localtv.models

class Command(BaseCommand):

    def handle(self, *args, **options):
        self.handle_sitelocation_emails()

    def handle_sitelocation_emails(self):
        column2template = {
            'video_allotment_warning_sent': (
                'localtv/admin/tiers_emails/video_allotment.txt', 'Upgrade your Miro Community site to store more video'),
            'free_trial_warning_sent': (
                'localtv/admin/tiers_emails/free_trial_warning_sent.txt', 'Only five more days left in your Miro Community free trial'),
            }
        for site_location_column in localtv.tiers.nightly_warnings():
            # Save a note saying we sent the notice
            sitelocation = localtv.models.SiteLocation.objects.get_current()
            setattr(sitelocation, site_location_column, True)
            sitelocation.save()

            template_name, subject = column2template[site_location_column] 
            localtv.tiers.send_tiers_related_email(subject, template_name)

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
        # We send this email to the person who owns the site. So we use
        # the tiers system's ability to send email.
        site_location = localtv.models.SiteLocation.objects.get_current()
        if site_location.already_sent_welcome_email:
            return

        # If we haven't sent it, prepare the email

        # Now send the sucker
        subject = "%s: Welcome to Miro Community"
        template = 'localtv/admin/ti

mark a note in the SiteLocation to indicate we have sent it
        site_location.already_sent_welcome_email = True
        site_location.save()

        
        

        localtv.tiers.send_tiers_related_email("

        for site_location_column in localtv.tiers.nightly_warnings():
            # Save a note saying we sent the notice
            sitelocation = localtv.models.SiteLocation.objects.get_current()
            setattr(sitelocation, site_location_column, True)
            sitelocation.save()

            template_name, subject = column2template[site_location_column] 
            localtv.tiers.send_tiers_related_email(subject, template_name, sitelocation)

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
        tier_info = localtv.models.TierInfo.objects.get_current()
        if tier_info.already_sent_welcome_email:
            return
        if 'temporarily_override_payment_due_date' in options:
            extra_context = {'next_payment_due_date': options['temporarily_override_payment_due_date'].strftime('%B %e, %Y'),
                             'in_free_trial': True}
        else:
            extra_context = {}
        self.actually_send(site_location, tier_info, extra_context)

    def actually_send(self, site_location, tier_info, extra_context):

        # If we haven't sent it, prepare the email

        # Now send the sucker
        subject = "%s: Welcome to Miro Community" % site_location.site.name
        if site_location.tier_name == 'basic':
            template = 'localtv/admin/tiers_emails/welcome_to_your_site_basic.txt'
        else:
            template = 'localtv/admin/tiers_emails/welcome_to_your_site.txt'
        localtv.tiers.send_tiers_related_multipart_email(subject, template, site_location, extra_context=extra_context)

        # Finally, save a note saying we sent it.
        tier_info.already_sent_welcome_email = True
        tier_info.save()

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
from django.core.mail import EmailMessage
from django.template import Context, loader
from django.contrib.auth.models import User

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

            # Send it to the site superuser with the lowest ID
            superusers = User.objects.filter(is_superuser=True)
            first_one = superusers.order_by('pk')[0]

            if sitelocation.payment_due_date:
                next_payment_due_date = sitelocation.payment_due_date.strftime('%Y-%m-%d')
            else:
                next_payment_due_date = None

            # Generate the email
            template_name, subject = column2template[site_location_column] 
            t = loader.get_template(template_name)
            c = Context({'site': sitelocation.site,
                         'video_count': localtv.tiers.current_videos_that_count_toward_limit(),
                         'short_name': first_one.first_name or first_one.username,
                         'next_payment_due_date': next_payment_due_date,
                         })
            message = t.render(c)

            # Send the sucker
            from django.conf import settings
            EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL,
                         [first_one.email]).send(fail_silently=False)

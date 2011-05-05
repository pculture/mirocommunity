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

import datetime
import logging

from django.core.management.base import BaseCommand

import localtv.tiers
import localtv.models
import localtv.management.commands.send_welcome_email

TOO_LONG = datetime.timedelta(minutes=30)

class Command(BaseCommand):

    def handle(self, *args, **options):
        # Is the site in a paid tier?
        sitelocation = localtv.models.SiteLocation.objects.get_current()
        if sitelocation.tierinfo.should_send_welcome_email_on_paypal_event:
            self.stop_waiting_if_we_have_to()

    def stop_waiting_if_we_have_to(self, now=None):
        if now is None:
            now = datetime.datetime.utcnow()

        ti = localtv.models.TierInfo.objects.get()
        if now > ti.waiting_on_payment_until:
            logging.warning("I'm done waiting on " +
                            localtv.models.SiteLocation.objects.get_current(
                    ).site.domain)
            self.actually_stop_waiting()

    def actually_stop_waiting(self):
        # Okay. We declare that we're done waiting...
        ti = localtv.models.TierInfo.objects.get()
        ti.waiting_on_payment_until = None
        ti.save()

        # We were probably expecting to send the welcome email out
        # but might have missed it. So we send it now:
        if ti.should_send_welcome_email_on_paypal_event:
            cmd = localtv.management.commands.send_welcome_email.Command()
            cmd.handle()

        ti.should_send_welcome_email_on_paypal_event = False
        ti.save()

# This file is part of Miro Community.
# Copyright (C) 2011 Participatory Culture Foundation
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

import traceback

from django.core.files.storage import default_storage
from django.core.management.base import NoArgsCommand
from django.db.models import Q

import localtv.models

class Command(NoArgsCommand):

    args = ''

    def handle_noargs(self, verbosity=0, **options):
        ### Reset the tiers state to:
        # - tier is basic
        # - all TierData is blank
        ### If you want a proper simulation of deployed sites, you should
        ### make sure to set settings.LOCALTV_DISABLE_TIERS_ENFORCEMENT to True
        sitelocation = localtv.models.SiteLocation.objects.get_current()
        tier_info = localtv.models.TierInfo.objects.get_current()

        sitelocation.tier_name = 'basic'
        sitelocation.save()

        tier_info.payment_due_date = None
        tier_info.free_trial_available = True
        tier_info.free_trial_started_on = None
        tier_info.in_free_trial = False
        tier_info.payment_secret = ''
        tier_info.get_payment_secret() # fill the payment secret field
        tier_info.current_paypal_profile_id = ''
        tier_info.video_allotment_warning_sent = False
        tier_info.free_trial_warning_sent = False
        tier_info.already_sent_welcome_email = False
        tier_info.inactive_site_warning_sent = False
        tier_info.user_has_successfully_performed_a_paypal_transaction = False
        tier_info.already_sent_tiers_compliance_email = False
        tier_info.fully_confirmed_tier_name = ''
        tier_info.save()

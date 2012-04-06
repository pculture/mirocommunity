# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2011, 2012 Participatory Culture Foundation
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

import sys
import time

from django.core.management.base import BaseCommand

import localtv.tiers
import localtv.models

class Command(BaseCommand):

    def handle(self, *args, **options):
        self.handle_check_for_invalid_ipn_state()
        self.handle_site_settings_emails()

    def handle_site_settings_emails(self):
        column2template = {
            'video_allotment_warning_sent': (
                'localtv/admin/tiers_emails/video_allotment.txt', 'Upgrade your Miro Community site to store more video'),
            'free_trial_warning_sent': (
                'localtv/admin/tiers_emails/free_trial_warning_sent.txt', 'Only five more days left in your Miro Community free trial'),
            'inactive_site_warning_sent': (
                'localtv/admin/tiers_emails/inactive_site_warning_sent.txt', 'Your Miro Community site has been inactive, come back!')
            }
        site_settings = localtv.models.SiteSettings.objects.get_current()

        for tier_info_column in localtv.tiers.nightly_warnings():
            # Save a note saying we sent the notice
            tier_info = localtv.models.TierInfo.objects.get_current()
            setattr(tier_info, tier_info_column, True)
            tier_info.save()

            template_name, subject = column2template[tier_info_column] 
            localtv.tiers.send_tiers_related_email(subject, template_name, site_settings)

    def handle_check_for_invalid_ipn_state(self):
        # Is the site in a paid tier?
        site_settings = localtv.models.SiteSettings.objects.get_current()

        # First of all: If the site is 'subsidized', then we skip the
        # rest of these checks.
        if site_settings.tierinfo.current_paypal_profile_id == 'subsidized':
            return

        # Okay. Well, the point of this isto check if the site is in a
        # paid tier but should not be.
        in_paid_tier = (site_settings.tier_name and
                        site_settings.tier_name != 'basic')

        # Is the free trial used up?
        # Note that premium sites have *not* used up their free trial.
        if (in_paid_tier and
            site_settings.tierinfo.free_trial_available and
            site_settings.tier_name == 'max'):

            print >> sys.stderr, (
                "UM YIKES, I THOUGHT THE SITE SHOULD BE SUBSIDIZED",
                site_settings.site.domain)
            return

        # Is there something stored in the
        # tier_info.current_paypal_profile_id? If so, great.
        if (in_paid_tier and
            not site_settings.tierinfo.current_paypal_profile_id and
            not site_settings.tierinfo.free_trial_available):
            # So, one reason this could happen is that PayPal is being really
            # slow to send us data over PDT.
            #
            # Maybe that's what's happening. Let's sleep for a few seconds.
            time.sleep(10)

            # Then re-do the check. If it still looks bad, then print a warning.
            if (in_paid_tier and
                not site_settings.tierinfo.current_paypal_profile_id and
                not site_settings.tierinfo.free_trial_available):
                print >> sys.stderr, ('This site looks delinquent: ',
                                      site_settings.site.domain)

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
        ti = localtv.models.TierInfo.objects.get_current()
        if ti.already_sent_tiers_compliance_email:
            return

        sitelocation = localtv.models.SiteLocation.objects.get_current()
        if localtv.tiers.user_warnings_for_downgrade(sitelocation.tier_name):
            localtv.tiers.send_tiers_related_email(
                'Whoa, this is a warning',
                'localtv/admin/tiers_emails/too_big_for_your_tier.txt',
                sitelocation)
            ti.already_sent_tiers_compliance_email = True
            ti.save()


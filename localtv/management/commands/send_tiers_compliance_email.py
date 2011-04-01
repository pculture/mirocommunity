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
import uploadtemplate.models

class Command(BaseCommand):

    def handle(self, *args, **options):
        ti = localtv.models.TierInfo.objects.get_current()
        if ti.already_sent_tiers_compliance_email:
            return

        sitelocation = localtv.models.SiteLocation.objects.get_current()
        warnings = localtv.tiers.user_warnings_for_downgrade(sitelocation.tier_name)
        ### Hack
        ### Override the customtheme warning for this email with custom code
        if 'customtheme' in warnings:
            warnings.remove('customtheme')
        default_non_bundled_themes = uploadtemplate.models.Theme.objects.filter(default=True, bundled=False)
        if default_non_bundled_themes:
            warnings.add('customtheme')

        ### Hack
        ### override the customdomain warning, too
        if (sitelocation.site.domain
            and not sitelocation.site.domain.endswith('mirocommunity.org')
            and not sitelocation.get_tier().permits_custom_domain()):
            warnings.add('customdomain')

        data = {'warnings': warnings}
        data['would_lose_admin_usernames'] = localtv.tiers.push_number_of_admins_down(sitelocation.get_tier().admins_limit())
        data['videos_over_limit'] = localtv.tiers.hide_videos_above_limit(sitelocation.get_tier())
        data['video_count'] = localtv.tiers.current_videos_that_count_toward_limit().count()
        localtv.tiers.send_tiers_related_multipart_email(
            'Changes to your Miro Community site',
            'localtv/admin/tiers_emails/too_big_for_your_tier.txt',
            sitelocation,
            extra_context=data)
        ti.already_sent_tiers_compliance_email = True
        ti.save()

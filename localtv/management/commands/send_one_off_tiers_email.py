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

import hashlib
import os.path
import sys
import re

from django.core.management.base import BaseCommand
import django.template
from django.conf import settings

import localtv.tiers
import localtv.models
import uploadtemplate.models

class Command(BaseCommand):
    args = '<template_name> <subject>'
    help = 'Sends a rich text email to the site admin, filling in template content with info from the tiers system'

    def _path_to_already_sent_file(self, template_name):
        hashed = hashlib.sha1(template_name).hexdigest()
        # Use the MEDIA_ROOT directory as where we store these notes
        base_dir = os.path.join(settings.MEDIA_ROOT, '.one-off-tiers-emails')
        if not os.path.exists(base_dir):
            os.mkdir(base_dir)
        return os.path.join(base_dir, hashed)

    def already_sent_this(self, template_name):
        return os.path.exists(self._path_to_already_sent_file(template_name))

    def mark_as_sent(self, template_name):
        file_obj = open(self._path_to_already_sent_file(template_name), 'w')
        file_obj.close()

    def handle(self, *args, **options):
        if len(args) != 2:
            print >> sys.stderr, "You have to specify a template name and subject. And that's it."
            sys.exit(1)

        html_template_name = args[0]
        subject = django.template.Template(args[1]).render(
                         django.template.Context({'site': localtv.models.SiteLocation.objects.get_current().site}))

        if not html_template_name.endswith('.html'):
            print >> sys.stderr, "Eek, it has to end with .html."
            sys.exit(1)

        # Check if we should skip it
        if self.already_sent_this(html_template_name):
            print >> sys.stderr, "Seems we have already sent this. Skipping."
            sys.exit(1)

        sitelocation = localtv.models.SiteLocation.objects.get_current()
        warnings = localtv.tiers.user_warnings_for_downgrade(sitelocation.tier_name)
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

        # Okay! We need to create the text template object, and the html template object,
        with file(html_template_name) as f:
            html_template_obj = django.template.Template(f.read())

        with file(re.sub('html$', 'txt', html_template_name)) as f:
            text_template_obj = django.template.Template(f.read())

        if warnings:
            localtv.tiers.send_tiers_related_multipart_email(subject, template_name=None,
                                                         sitelocation=localtv.models.SiteLocation.objects.get_current(),
                                                         override_text_template=text_template_obj,
                                                         override_html_template=html_template_obj,
                                                         extra_context=data)

        else:
            print >> sys.stderr, "This site does not have any warnings, so, like, whatever."

        self.mark_as_sent(html_template_name)

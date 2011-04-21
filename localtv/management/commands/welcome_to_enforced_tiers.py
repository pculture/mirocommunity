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

import sys
import hashlib
import os.path
import re
import simplejson

from django.core.management.base import BaseCommand
from django.conf import settings
import django.template

import localtv.tiers
import localtv.models

## This is some horrifying hackish copy-paste between send_one_off_tiers_email
## and send_tiers_compliance_email.

class Command(BaseCommand):

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
        if len(args) != 1:
            print >> sys.stderr, "You have to specify a template name. And that's it."
            sys.exit(1)

        html_template_name = args[0]
        subject_unformatted = 'Important: Changes to {% firstof site.name site.domain %}'
        subject = django.template.Template(subject_unformatted).render(
                         django.template.Context({'site': localtv.models.SiteLocation.objects.get_current().site}))

        if not html_template_name.endswith('.html'):
            print >> sys.stderr, "Eek, it has to end with .html."
            sys.exit(1)

        # Check if we should skip it
        if self.already_sent_this(html_template_name):
            print >> sys.stderr, "Seems we have already sent this. Skipping."
            sys.exit(1)

        sitelocation = localtv.models.SiteLocation.objects.get_current()

        # Check if the site is, for some reason, still in no_enforce mode.
        # If enforcement is disabled, bail out.
        if not sitelocation.enforce_tiers():
            print >> sys.stderr, "Enforcement is disabled. Bailing out now!"
            return

        if sitelocation.tier_name != 'basic':
            print >> sys.stderr, "Um um um the site should really be in basic."
            print >> sys.stderr, "Bailing out."
            return

        if sitelocation.tierinfo.site_is_subsidized():
            print >> sys.stderr, "Seems the site is subsidized. Skipping."
            self.mark_as_sent(html_template_name)
            return

        warnings = localtv.tiers.user_warnings_for_downgrade(sitelocation.tier_name)
        # There is no reason to hack these warnings. They are the real deal.

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
            # Well, there were warnings. That means that, sadly, it is time
            # to squish the site down to size.

            # Will we unpublish videos? If so, save a quick note about them.
            new_limit = sitelocation.get_tier().videos_limit()
            current_count = localtv.tiers.current_videos_that_count_toward_limit(
                ).count()
            if current_count <= new_limit:
                count = 0
            count = (current_count - new_limit)

            if count > 0:
                # Okay, so we're going to squish the video count down.
                disable_these_videos = localtv.tiers.current_videos_that_count_toward_limit().order_by('pk')[:count]
                disable_these_pks = list(disable_these_videos.values_list('id', flat=True))
                as_json = simplejson.dumps(disable_these_pks)
                filename = os.path.join('/var/tmp/', 'videos-disabled-' + hashlib.sha1(sitelocation.site.domain).hexdigest() + '.json')
                file_obj = open(filename, 'w')
                file_obj.write(as_json)
                file_obj.close()

            # Okay. Now actually squish the site down to size.
            localtv.tiers.pre_save_adjust_resource_usage(sitelocation, signal=None)

        else:
            print >> sys.stderr, "This site does not have any warnings, so, like, whatever."

        self.mark_as_sent(html_template_name)

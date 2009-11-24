# Copyright 2009 - Participatory Culture Foundation
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

import os.path
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):

    args = '[version]'
    help = 'Freeze the current templates and static resources.'

    def handle(self, *args, **kwargs):
        if len(args) != 1 or not args[0]:
            raise CommandError('You must provide a version string.')

        version = args[0]

        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../../..'))
        versioned_static_dir = os.path.join(repo_root, 'static', 'versioned',
                                            version)
        versioned_templates_dir = os.path.join(repo_root, 'localtv',
                                               'versioned_templates',
                                               version)

        if os.path.exists(versioned_static_dir) or os.path.exists(
            versioned_templates_dir):
            raise CommandError('version %s is already frozen' % version)

        os.makedirs(versioned_static_dir)

        for static_path in ('css', 'images', 'js', 'swf'):
            shutil.copytree(
                os.path.join(repo_root, 'static', static_path),
                os.path.join(versioned_static_dir, static_path))

        for template_dir in settings.TEMPLATE_DIRS[::-1]:
            # do it in reverse order, so that the first template that would
            # load overwrites the others
            if versioned_templates_dir.startswith(
                os.path.realpath(template_dir)):
                continue
            if not os.path.exists(template_dir):
                continue
            shutil.copytree(template_dir, versioned_templates_dir)

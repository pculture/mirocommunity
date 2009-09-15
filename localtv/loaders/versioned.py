# Miro Community
# Copyright 2009 - Participatory Culture Foundation
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# based on django.templates.loaders.filesystem
# imports # {{{
from django.conf import settings
from django.template import TemplateDoesNotExist
from django.utils._os import safe_join

def get_template_sources(template_name, template_dirs=None):
    if not template_dirs:
        template_dirs = settings.TEMPLATE_DIRS
    if not getattr(settings, 'USE_VERSION', False):
        return
    version = settings.USE_VERSION + '/'
    for template_dir in template_dirs:
        try:
            yield safe_join(template_dir, version + template_name)
        except ValueError:
            # The joined path was located outside of template_dir.
            pass

def load_template_source(template_name, template_dirs=None):
    tried = []
    for filepath in get_template_sources(template_name, template_dirs):
        try:
            return (open(filepath).read().decode(settings.FILE_CHARSET),
                    filepath)
        except IOError:
            tried.append(filepath)
    if tried:
        error_msg = "Tried %s" % tried
    else:
        error_msg = "Your TEMPLATE_DIRS setting is empty. Change it to point "\
            "to at least one template directory."
    raise TemplateDoesNotExist, error_msg

load_template_source.is_usable = True

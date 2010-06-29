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

from localtv.decorators import require_site_admin

from uploadtemplate import views, models

index = require_site_admin(views.index)
delete = require_site_admin(views.delete)
download = require_site_admin(views.download)
set_default = require_site_admin(views.set_default)

def filter_admin_files(sender, file_paths=None, **kwargs):
    to_remove = []
    for path in file_paths:
        if '/admin' in path:
            to_remove.append(path)
        elif '/inline_edit' in path:
            to_remove.append(path)
        elif '/uploadtemplate/' in path:
            to_remove.append(path)
        elif '/flatpages/' in path:
            to_remove.append(path)
        elif '/comments/' in path:
            if 'spam' in path or 'moderation_queue' in path or \
                    path.endswith('.txt'):
                to_remove.append(path)
        elif '/static/js/tiny_mce/' in path:
            to_remove.append(path)
        elif path.endswith('~'):
            to_remove.append(path)
        elif '_flymake.' in path:
            to_remove.append(path)
    return to_remove

models.pre_zip.connect(filter_admin_files, weak=False)

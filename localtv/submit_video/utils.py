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

import httplib
import urlparse

from vidscraper.utils.mimetypes import is_accepted_type, is_accepted_filename

def is_video_url(url):
    """
    If the URL represents a video file, this function returns True.

    1) It checks the extension to see if it's in VIDEO_EXTENSIONS
    2) It performs an HTTP HEAD request and checks the MIME type with
       is_accepted_type()
    """
    if is_accepted_filename(url):
        return True

    parsed = urlparse.urlparse(url)
    if parsed.scheme == 'http':
        conn = httplib.HTTPConnection(parsed.netloc)
    elif parsed.scheme == 'https':
        conn = httplib.HTTPSConnection(parsed.netloc)
    else:
        return False
    conn.request('HEAD', parsed.path)
    response = conn.getresponse()

    mimetype = response.getheader('Content-Type', '')
    return is_accepted_type(mimetype)

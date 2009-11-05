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

import re

from localtv import filetypes


def to_utf8(feedparser_string):
    if str is None:
        return None
    elif isinstance(feedparser_string, str):
        try:
            decoded = feedparser_string.decode('utf-8')
        except UnicodeError:
            try:
                decoded = feedparser_string.decode('latin-1')
            except UnicodeError:
                decoded = feedparser_string.decode('utf-8', 'ignore')
        return decoded.encode('utf-8')
    elif isinstance(feedparser_string, unicode):
        return feedparser_string.encode('utf-8')


def has_video_type(enclosure):
    try:
        type = enclosure['type']
    except KeyError:
        return False
    application_video_mime_types = [
        "application/ogg", 
        "application/x-annodex",
        "application/x-bittorrent", 
        "application/x-shockwave-flash"
    ]
    return (type.startswith('video/') or type.startswith('audio/') or
            type in application_video_mime_types)


def get_first_video_enclosure(entry):
    """Find the first video enclosure in a feedparser entry.  Returns the
    enclosure, or None if no video enclosure is found.
    """
    enclosures = entry.get('media_content') or entry.get('enclosures')
    if not enclosures:
        return None
    best_enclosure = None
    for enclosure in enclosures:
        if has_video_type(enclosure) or \
                filetypes.isAllowedFilename(enclosure.url):
            if enclosure.get('isdefault'):
                return enclosure
            elif best_enclosure is None:
                best_enclosure = enclosure
    return best_enclosure


def get_thumbnail_url(entry):
    """Get the URL for a thumbnail from a feedparser entry."""
    # Try the video enclosure
    def _get(d):
        if 'media_thumbnail' in d:
            return d.media_thumbnail[0]['url']
        if 'blip_thumbnail_src' in d and d.blip_thumbnail_src:
            return 'http://a.images.blip.tv/' + to_utf8(
                d['blip_thumbnail_src'])
        raise KeyError
    video_enclosure = get_first_video_enclosure(entry)
    if video_enclosure is not None:
        try:
            return _get(video_enclosure)
        except KeyError:
            pass
    # Try to get any enclosure thumbnail
    for key in 'media_content', 'enclosures':
        if key in entry:
            for enclosure in entry[key]:
                try:
                    return _get(enclosure)
                except KeyError:
                    pass
    # Try to get the thumbnail for our entry
    try:
        return _get(entry)
    except KeyError:
        pass

    if entry.get('link', '').find(u'youtube.com') != -1:
        if 'content' in entry:
            content = entry.content[0]['value']
        else:
            content = entry.summary
        match = re.search(r'<img alt="" src="([^"]+)" />',
                          content)
        if match:
            return match.group(1)

    return None

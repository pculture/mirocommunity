# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2009, 2010, 2011, 2012 Participatory Culture Foundation
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

class LocaltvException(Exception):
    """Base class for :mod:`localtv` exceptions."""
    pass


class InvalidVideo(LocaltvException):
    """
    Raised if a :class:`.Video` instance can't be created from a
    :class:`vidscraper.videos.Video` instance.

    """
    pass


class CannotOpenImageUrl(LocaltvException):
    """Raised if a thumbnail cannot be processed."""
    pass

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

from django.dispatch import Signal


#: This signal is fired when a :class:`.Video` is built from a
#: :class:`vidscraper.suites.base.Video`. It provides the following
#: arguments:
#:
#: - ``instance``: The created :class:`.Video` instance. This instance will not
#:                 have been saved.
#: - ``vidscraper_video``: The :class:`vidscraper.suites.base.Video` instance
#                          it was created from.
post_video_from_vidscraper = Signal(providing_args=["instance",
                                                    "vidscraper_video",
                                                    "using"])


#: This signal is fired when a :class:`.Video` is successfully submitted.
#: TODO: Depending on what happens with submit_video, this should perhaps be
#: moved elsewhere.
submit_finished = Signal()

# This signal is first from the mark_import_pending task, to optionally filter
# what videos should be marked as active.
pre_mark_as_active = Signal(providing_args=['active_set'])

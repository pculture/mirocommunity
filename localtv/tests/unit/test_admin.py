# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2010, 2011, 2012 Participatory Culture Foundation
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

from django.contrib.sites.models import Site

from localtv.admin.forms import AddFeedForm
from localtv.tests import BaseTestCase


class AddFeedTestCase(BaseTestCase):
    def test_duplicate_feed_url(self):
        site = Site.objects.get_current()
        url = 'http://google.com/'
        self.create_feed(url, site_id=site.pk)
        form = AddFeedForm(data={'feed_url': url, 'auto_approve': True})
        self.assertTrue(form.is_bound)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors.get('feed_url'),
                         ["Feed with this URL already exists."])

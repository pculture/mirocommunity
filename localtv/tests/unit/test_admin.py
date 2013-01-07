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

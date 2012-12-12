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

from __future__ import with_statement

from daguerre.models import Image, AdjustedImage
from django.contrib.sites.models import Site
from django.core.files.base import File

from localtv.models import SiteSettings, SiteRelatedManager, WidgetSettings
from localtv.tests import BaseTestCase


class SiteRelatedManagerTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.assertIsInstance(SiteSettings.objects, SiteRelatedManager)

    def test_post_save(self):
        """
        When an object is saved, it should be cached according to the site's pk,
        not its own.

        """
        site = Site.objects.get_current()
        site_settings = SiteSettings.objects.create(site=site, pk=site.pk + 1)
        using = site_settings._state.db
        cache = SiteSettings.objects._cache
        self.assertTrue((using, site.pk) in cache)
        self.assertTrue(cache[(using, site.pk)] is site_settings)

    def test_get_cached__cached(self):
        """
        If the instance is already cached, we shouldn't need any queries.

        """
        site = Site.objects.get_current()
        site_settings = SiteSettings.objects.create(site=site)
        using = site_settings._state.db

        with self.assertNumQueries(0):
            site_settings2 = SiteSettings.objects.get_cached(site.pk, using)
            self.assertTrue(site_settings2 is site_settings)

    def test_get_cached__fetch(self):
        """
        If the instance exists but isn't cached, we should need one query.

        """
        site = Site.objects.get_current()
        site_settings = SiteSettings.objects.create(site=site)
        SiteSettings.objects.clear_cache()
        using = site_settings._state.db

        with self.assertNumQueries(1):
            site_settings2 = SiteSettings.objects.get_cached(site.pk, using)
            self.assertFalse(site_settings2 is site_settings)
            self.assertEqual(site_settings2, site_settings)

    def test_get_cached__create(self):
        """
        If the instance doesn't exist, we should need three queries: one
        attempt to fetch, one fetch of the site, and one creation.

        """
        site = Site.objects.get_current()
        using = 'default'

        with self.assertNumQueries(3):
            site_settings = SiteSettings.objects.get_cached(site.pk, using)
            self.assertEqual(site_settings._state.db, using)
            self.assertEqual(site_settings.site, site)

    def test_get_current(self):
        """
        get_current should return a cached instance related to the current
        site.

        """
        site = Site.objects.get_current()

        # At first, there isn't even a database object.
        with self.assertNumQueries(3):
            site_settings = SiteSettings.objects.get_current()

        SiteSettings.objects.clear_cache()

        with self.assertNumQueries(1):
            site_settings2 = SiteSettings.objects.get_current()

        with self.assertNumQueries(0):
            site_settings3 = SiteSettings.objects.get_current()

        self.assertEqual(site_settings, site_settings2)
        self.assertTrue(site_settings2 is site_settings3)
        self.assertEqual(site_settings.site, site)
        self.assertEqual(site_settings._state.db, 'default')


class WidgetSettingsModelTestCase(BaseTestCase):

    def test__get_current(self):
        """
        get_current should return an instance related to the current
        site.
        """
        site = Site.objects.get()

        widget_settings = WidgetSettings.objects.get_current()

        self.assertEqual(widget_settings.site, site)
        self.assertEqual(widget_settings._state.db, 'default')

    def test_icon(self):
        """
        Creating a WidgetSettings should copy the logo from the SiteSettings
        object.
        """
        WidgetSettings.objects.all().delete()
        WidgetSettings.objects.clear_cache()

        site_settings = SiteSettings.objects.get_current()
        site_settings.logo = File(self._data_file('logo.png'))
        site_settings.save()

        widget_settings = WidgetSettings.objects.get_current()

        widget_settings.icon.open()
        site_settings.logo.open()
        widget_icon = widget_settings.icon.read()
        site_settings_logo = site_settings.logo.read()
        self.assertEqual(len(widget_icon),
                         len(site_settings_logo))
        self.assertEqual(widget_icon, site_settings_logo)
        self.assertTrue(widget_settings.has_thumbnail)


class ThumbnailableTestCase(BaseTestCase):
    def save_thumbnail__deletes(self):
        """
        Saving a new thumbnail should delete all cached thumbnail resizes.

        """
        video = self.create_video()
        video.save_thumbnail_from_file(File(self._data_file('logo.png')))
        image1 = Image.objects.for_storage_path(video.thumbnail_path)
        AdjustedImage.objects.adjust(image1, width=image1.width / 2)
        self.assertTrue(image1.adjustedimage_set.all())
        video.save_thumbnail_from_file(File(self._data_file('logo.png')))
        image2 = Image.objects.for_storage_path(video.thumbnail_path)
        self.assertFalse(image2.adjustedimage_set.all())

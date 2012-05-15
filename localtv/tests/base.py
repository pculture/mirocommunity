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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community. If not, see <http://www.gnu.org/licenses/>.

import os
from datetime import datetime, timedelta
from socket import getaddrinfo
from urllib import quote_plus, urlencode

from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.sites.models import Site
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.management import call_command
from django.db import transaction
from django.template.defaultfilters import slugify
from django.test.testcases import (TestCase, _deferredSkip,
                                   disable_transaction_methods,
                                   restore_transaction_methods,
                                   connections_support_transactions)
from django.test.client import Client, RequestFactory
from haystack import connections
from tagging.models import Tag

from localtv import models
from localtv.middleware import UserIsAdminMiddleware
from localtv.playlists.models import Playlist


#: Global variable for storing whether the current global state believe that
#: it's connected to the internet.
HAVE_INTERNET_CONNECTION = None

class FakeRequestFactory(RequestFactory):
    """Constructs requests with any necessary attributes set."""
    def request(self, user=None, **request):
        request = super(FakeRequestFactory, self).request(**request)
        if user is None:
            request.user = AnonymousUser()
        else:
            request.user = user
        UserIsAdminMiddleware().process_request(request)
        SessionMiddleware().process_request(request)
        return request


class BaseTestCase(TestCase):
    @staticmethod
    def _clear_index():
        """Clears the search index."""
        backend = connections['default'].get_backend()
        backend.clear()

    @staticmethod
    def _update_index():
        """Updates the search index."""
        backend = connections['default'].get_backend()
        index = connections['default'].get_unified_index().get_index(
            models.Video)
        qs = index.index_queryset()
        if qs:
            backend.update(index, qs)

    @classmethod
    def _rebuild_index(cls):
        """Clears and then updates the search index."""
        cls._clear_index()
        cls._update_index()

    @staticmethod
    def _disable_index_updates():
        """Disconnects the index update listeners."""
        index = connections['default'].get_unified_index().get_index(
                                                                 models.Video)
        index._teardown_save()
        index._teardown_delete()

    @staticmethod
    def _enable_index_updates():
        """Connects the index update listeners."""
        index = connections['default'].get_unified_index().get_index(
                                                                 models.Video)
        index._setup_save()
        index._setup_delete()

    @staticmethod
    def _start_test_transaction():
        if connections_support_transactions():
            transaction.enter_transaction_management(using='default')
            transaction.managed(True, using='default')
        else:
            call_command('flush', verbosity=0, interactive=False,
                         database='default')
        disable_transaction_methods()

    @staticmethod
    def _end_test_transaction():
        restore_transaction_methods()
        if connections_support_transactions():
            transaction.rollback(using='default')
            transaction.leave_transaction_management(using='default')

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.factory = FakeRequestFactory()
        models.SiteSettings.objects.clear_cache()

    @classmethod
    def reload_from_db(self, *objects):
        def r(o):
            return o.__class__.objects.get(pk=o.pk)
        if len(objects) == 1:
            return r(objects[0])
        else:
            return [r(o) for o in objects]

    @classmethod
    def create_video(cls, name='Test.', status=models.Video.ACTIVE, site_id=1,
                     watches=0, categories=None, authors=None, tags=None,
                     update_index=True, load_from_db=False, **kwargs):
        """
        Factory method for creating videos. Supplies the following defaults:

        * name: 'Test'
        * status: :attr:`Video.ACTIVE`
        * site_id: 1

        In addition to kwargs for the video's fields, which are passed directly
        to :meth:`Video.objects.create`, takes a ``watches`` kwarg (defaults to
        0). If ``watches`` is greater than 0, that many :class:`.Watch`
        instances will be created, each successively one day further in the
        past.

        List of category and author instances may also be passed in as
        ``categories`` and ``authors``, respectively.

        """
        video = models.Video(name=name, status=status, site_id=site_id,
                             **kwargs)
        video.save(update_index=update_index)

        for i in xrange(watches):
            cls.create_watch(video, days=i)

        if categories is not None:
            video.categories.add(*categories)

        if authors is not None:
            video.authors.add(*authors)

        if tags is not None:
            video.tags = tags

        # Update the index here to be sure that the categories and authors get
        # indexed correctly.
        if update_index and status == models.Video.ACTIVE and site_id == 1:
            index = connections['default'].get_unified_index().get_index(
                models.Video)
            index._enqueue_update(video)

        return video

    @classmethod
    def create_category(cls, name='Category', slug=None, site_id=1, **kwargs):
        """
        Factory method for creating categories. Supplies the following
        default:

        * site_id: 1

        Additionally, ``slug`` will be auto-generated from ``name`` if not
        provided. All arguments given are passed directly to
        :meth:`Category.objects.create`.

        """
        if slug is None:
            slug = slugify(name)
        return models.Category.objects.create(name=name, slug=slug,
                                              site_id=site_id, **kwargs)

    @classmethod
    def create_user(cls, **kwargs):
        """
        Factory method for creating users. All arguments are passed directly
        to :meth:`User.objects.create`.

        """
        return User.objects.create(**kwargs)

    @classmethod
    def create_tag(cls, **kwargs):
        """
        Factory method for creating tags. All arguments are passed directly
        to :meth:`Tag.objects.create`.

        """
        return Tag.objects.create(**kwargs)

    @classmethod
    def create_watch(cls, video, ip_address='0.0.0.0', days=0):
        """
        Factory method for creating :class:`Watch` instances.

        :param video: The video for the :class:`Watch`.
        :param ip_address: An IP address for the watcher.
        :param days: Number of days to place the :class:`Watch` in the past.

        """
        watch = models.Watch.objects.create(video=video, ip_address=ip_address)
        watch.timestamp = datetime.now() - timedelta(days)
        watch.save()
        return watch

    @classmethod
    def create_feed(cls, feed_url, name=None, description='Lorem ipsum',
                    last_updated=None, status=models.Feed.ACTIVE, site_id=1,
                    **kwargs):
        if name is None:
            name = feed_url
        if last_updated is None:
            last_updated = datetime.now()
        return models.Feed.objects.create(feed_url=feed_url,
                                          name=name,
                                          description=description,
                                          last_updated=last_updated,
                                          status=status,
                                          site_id=site_id,
                                          **kwargs)

    @classmethod
    def create_playlist(cls, user, name='Playlist', status=Playlist.PUBLIC,
                        site_id=1, slug=None, description=''):
        if slug is None:
            slug = slugify(name)
        return Playlist.objects.create(name=name, status=status,
                                       site_id=site_id, user=user, slug=slug,
                                       description=description)

    @classmethod
    def create_search(cls, query_string, site_id=1, **kwargs):
        return models.SavedSearch.objects.create(query_string=query_string,
                                                 site_id=site_id,
                                                 **kwargs)

    @classmethod
    def create_site(cls, domain='example.com', name=None):
        if name is None:
            name = domain

        return Site.objects.create(domain=domain, name=name)

    @staticmethod
    def _data_file(filename):
        """
        Returns the absolute path to a file in our testdata directory.
        """
        return os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                'testdata',
                filename))

    def assertRequiresAuthentication(self, url, *args,
                                     **kwargs):
        """
        Assert that the given URL requires the user to be authenticated.

        If additional arguments are passed, they are passed to the Client.get
        method

        If keyword arguments are present, they're passed to Client.login before
        the URL is accessed.

        @param url_or_reverse: the URL to access
        """
        c = Client()

        if kwargs:
            c.login(**kwargs)

        response = c.get(url, *args)
        if args and args[0]:
            url = '%s?%s' % (url, urlencode(args[0]))
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s?next=%s' %
                          ('testserver',
                           settings.LOGIN_URL,
                           quote_plus(url, safe='/')))

    def assertStatusCodeEquals(self, response, status_code):
        """
        Assert that the response has the given status code.  If not, give a
        useful error mesage.
        """
        self.assertEqual(response.status_code, status_code,
                          'Status Code: %i != %i\nData: %s' % (
                response.status_code, status_code,
                response.content or response.get('Location', '')))

    def assertDictEqual(self, data, expected_data, msg=None):
        errors = []
        keys = set(data)
        expected_keys = set(expected_data)

        missing_keys = expected_keys - keys
        if missing_keys:
            errors.append('Expected keys missing')
            errors.append('=====================')
            errors.extend(('{0}: {1}'.format(key, expected_data[key])
                           for key in missing_keys))
            errors.append('')

        added_keys = keys - expected_keys
        if added_keys:
            errors.append('Unexpected keys found')
            errors.append('=====================')
            errors.extend(('{0}: {1}'.format(key, data[key])
                           for key in added_keys))
            errors.append('')

        shared_keys = keys & expected_keys
        if shared_keys:
            for key in shared_keys:
                if data[key] != expected_data[key]:
                    errors.append('value for {0} not equal:\n'
                                  '{1!r} != {2!r}'.format(
                                  key, data[key], expected_data[key]))

        if errors:
            errors = ['Dictionaries not equal', ''] + errors
            raise AssertionError('\n'.join(errors))


def _have_internet_connection():
    global HAVE_INTERNET_CONNECTION

    if HAVE_INTERNET_CONNECTION is None:
        try:
            getaddrinfo("google.com", "http")
        except IOError:
            HAVE_INTERNET_CONNECTION = False
        else:
            HAVE_INTERNET_CONNECTION = True

    return HAVE_INTERNET_CONNECTION


def skipUnlessInternet():
    """
    Skip a test unless it seems like the machine running the test is
    connected to the internet.

    """
    return _deferredSkip(lambda: not _have_internet_connection(),
                         "Not connected to the internet.")

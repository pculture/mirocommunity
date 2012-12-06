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
import urlparse

from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.sites.models import Site
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.management import call_command
from django.db import transaction
from django.http import QueryDict
from django.template.defaultfilters import slugify
from django.test.testcases import (TestCase, _deferredSkip,
                                   disable_transaction_methods,
                                   restore_transaction_methods,
                                   connections_support_transactions)
from django.test.client import Client, RequestFactory
from haystack import connections
from tagging.models import Tag

import localtv
from localtv import models
from localtv.middleware import UserIsAdminMiddleware
from localtv.playlists.models import Playlist


#: Global variable for storing whether the current global state believe that
#: it's connected to the internet.
HAVE_INTERNET_CONNECTION = None

TEST_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(localtv.__file__), 'tests', 'data'))


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
    def create_video(cls, name='Test.', status=models.Video.ACTIVE, site_id=1,
                     watches=0, categories=None, authors=None, tags=None,
                     update_index=True, **kwargs):
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
    def create_user(cls, username='user', password=None, **kwargs):
        """
        Factory method for creating users. A default is provided for the
        username; if a password is provided, it will be assigned to the user
        with the set_password method.

        """
        user = User(username=username, **kwargs)
        if password is not None:
            user.set_password(password)
        user.save()
        return user

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

    @classmethod
    def _data_path(cls, test_path):
        """
        Given a path relative to localtv/tests/data, returns an absolute path.

        """
        return os.path.join(TEST_DATA_DIR, test_path)

    @classmethod
    def _data_file(cls, test_path, mode='r'):
        """
        Given a path relative to localtv/tests/data, returns an open file.

        """
        return open(cls._data_path(test_path), mode)

    def assertRedirects(self, response, target_path, netloc='testserver'):
        """
        Asserts that the given response represents a redirect to the target
        path at the given ``netloc``. By default, ``netloc`` will be
        'testserver', which corresponds to test-local urls.
        """
        self.assertEqual(response.status_code, 302)
        parsed_url = urlparse.urlsplit(response['Location'])
        parsed_target = urlparse.urlsplit(target_path)
        self.assertEqual(parsed_url.netloc, netloc)
        self.assertEqual(parsed_url.path, parsed_target.path)
        self.assertEqual(urlparse.parse_qs(parsed_url.query),
                         urlparse.parse_qs(parsed_target.query))

    def assertRequiresAuthentication(self, url, username=None, password=None,
                                     data=None):
        """
        Assert that the given URL requires the user to be authenticated.

        Since we can't check this directly, we actually check whether
        accessing the view (with credentials, if given) redirects to the login
        view (determined by the LOGIN_URL setting).

        :param url: The url to access.
        :param username: A username to use for login.
        :param password: A password to use for login.

        Any additional arguments will be passed to the test client's get()
        method.

        """
        c = Client()

        if username is not None and password is not None:
            c.login(username=username, password=password)

        response = c.get(url, data or {})
        parsed_url = urlparse.urlsplit(response['Location'])
        expected_url = "{path}?{qs}".format(path=settings.LOGIN_URL,
                                            qs=parsed_url.query)
        self.assertRedirects(response, expected_url)
        qd = QueryDict(parsed_url.query)
        parsed_next = urlparse.urlsplit(qd['next'])
        self.assertEqual(parsed_next.path, url)
        self.assertEqual(QueryDict(parsed_next.query).dict(), data or {})

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

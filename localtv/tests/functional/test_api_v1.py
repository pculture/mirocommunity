import json

from django.conf import settings
from django.core.files import File

from localtv.tests import BaseTestCase

from localtv.models import Feed, SavedSearch, Video

class ApiV1TestCase(BaseTestCase):
    """
    We test with static urls since consumers of the api will be doing the
    same. Our concern is not whether the API provides all the expected urls -
    that's a job for tastypie itself - but rather, whether the API provides
    the data we'd expect for each type of resource.

    """
    maxDiff = None

    def test_user(self):
        expected_data = {
            'id': '1',
            'username': 'user',
            'first_name': 'Foo',
            'last_name': 'Bar'
        }
        self.create_user(**expected_data)
        url = '/api/v1/user/1/'
        expected_data['resource_uri'] = url
        response = self.client.get('{0}?format=json'.format(url))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data, expected_data)

    def test_category(self):
        expected_data = {
            'id': '1',
            'name': 'Test',
            'slug': 'test',
            'logo': 'localtv/logos/png.png',
            'description': 'Lorem ipsum'
        }
        self.create_category(**expected_data)
        url = '/api/v1/category/1/'
        expected_data['resource_uri'] = url
        expected_data['logo'] = '{0}{1}'.format(settings.MEDIA_URL,
                                                expected_data['logo'])
        response = self.client.get('{0}?format=json'.format(url))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data, expected_data)

    def test_feed(self):
        expected_data = {
            'id': '1',
            'auto_approve': True,
            'auto_update': True,
            'feed_url': 'http://google.com',
            'name': 'Test',
            'webpage': 'http://google.com',
            'description': 'Lorem ipsum',
            'etag': '',
        }
        feed = self.create_feed(
            thumbnail=File(self._data_file('logo.png')),
            **expected_data)
        # get the data from the database; this makes sure the datetimes are the
        # same when we're using MySQL.
        feed = Feed.objects.get(pk=feed.pk)
        expected_data['thumbnail'] = feed.thumbnail.url
        url = '/api/v1/feed/1/'
        expected_data['resource_uri'] = url
        for attr in ('last_updated', 'when_submitted'):
            expected_data[attr] = getattr(feed, attr).isoformat()
        response = self.client.get('{0}?format=json'.format(url))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data, expected_data)

    def test_search(self):
        expected_data = {
            'id': '1',
            'auto_approve': True,
            'auto_update': True,
            'query_string': 'dead -parrot',
        }
        search = self.create_search(
            thumbnail=File(self._data_file('logo.png')),
            **expected_data)
        # get the data from the database; this makes sure the datetimes are the
        # same when we're using MySQL.
        search = SavedSearch.objects.get(pk=search.pk)
        expected_data['thumbnail'] = search.thumbnail.url
        url = '/api/v1/search/1/'
        expected_data['resource_uri'] = url
        expected_data['when_created'] = search.when_created.isoformat()
        response = self.client.get('{0}?format=json'.format(url))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data, expected_data)

    def test_video(self):
        expected_data = {
            'id': '1',
            'file_url': 'hi',
            'website_url': 'http://google.com',
            'embed_code': '',
            'guid': '12345',
            'tags': '',
        }
        video = self.create_video(
            thumbnail=File(self._data_file('logo.png')),
            update_index=False,
            **expected_data)
        # get the data from the database; this makes sure the datetimes are the
        # same when we're using MySQL.
        video = Video.objects.get(pk=video.pk)
        expected_data.update({
            'thumbnail': video.thumbnail.url,
            'tags': [],
            'feed': None,
            'search': None,
            'user': None,
            'authors': [],
            'categories': [],
            'when_featured': None,
        })
        url = '/api/v1/video/1/'
        expected_data['resource_uri'] = url
        for attr in ('when_modified', 'when_submitted', 'when_published'):
            dt = getattr(video, attr)
            if dt is not None:
                dt = dt.isoformat()
            expected_data[attr] = dt
        response = self.client.get('{0}?format=json'.format(url))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data, expected_data)

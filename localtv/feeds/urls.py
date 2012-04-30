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

from django.conf.urls.defaults import patterns, url, include

from localtv.feeds import views


def feed_urls(pattern, feed_class, kwargs=None, name=None):
    return patterns('',
        url(r'^{0}/?$'.format(pattern), feed_class(), kwargs, name),
        url(r'^json/{0}/?$'.format(pattern), feed_class(json=True), kwargs,
            "{0}_json".format(name))
    )


urlpatterns = patterns('',
    url(r'', include(feed_urls(r'new',
                               views.NewVideosFeed,
                               {'sort': 'newest'},
                               name='localtv_feeds_new'))),
    url(r'', include(feed_urls(r'featured',
                               views.FeaturedVideosFeed,
                               {'sort': 'featured'},
                               name='localtv_feeds_featured'))),
    url(r'', include(feed_urls(r'popular',
                               views.PopularVideosFeed,
                               {'sort': 'popular'},
                               name='localtv_feeds_popular'))),
    url(r'', include(feed_urls(r'category/(?P<slug>[\w-]+)',
                               views.CategoryVideosFeed,
                               name='localtv_feeds_category'))),
    url(r'', include(feed_urls(r'author/(?P<pk>\d+)',
                               views.AuthorVideosFeed,
                               name='localtv_feeds_author'))),
    url(r'', include(feed_urls(r'videos-imported-from/(?P<pk>\d+)',
                               views.FeedVideosFeed,
                               name='localtv_feeds_feed'))),
    url(r'', include(feed_urls(r'tag/(?P<name>.+)',
                               views.TagVideosFeed,
                               name='localtv_feeds_tag'))),
    url(r'', include(feed_urls(r'search/(.+)',
                               views.SearchVideosFeed,
                               name='localtv_feeds_search'))),
    url(r'', include(feed_urls(r'playlist/(?P<pk>\d+)',
                               views.PlaylistVideosFeed,
                               name='localtv_feeds_playlist'))),
)

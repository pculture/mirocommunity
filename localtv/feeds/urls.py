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

from django.conf.urls.defaults import patterns, url, include

from localtv.feeds import views


def make_patterns(suffix, name, feed_class):
    return patterns('',
        url(r'^%s$' % suffix, feed_class(), name=name),
        url(r'^json/%s$' % suffix, feed_class(json=True), name="%s_json" % name)
    )


urlpatterns = patterns('',
    url(r'', include(make_patterns(r'new', 'localtv_feeds_new',
                                    views.NewVideosFeed))),
    url(r'', include(make_patterns(r'featured', 'localtv_feeds_featured',
                                    views.FeaturedVideosFeed))),
    url(r'', include(make_patterns(r'popular', 'localtv_feeds_popular',
                                    views.PopularVideosFeed))),
    url(r'', include(make_patterns(r'category/([\w-]+)',
                                    'localtv_feeds_category',
                                    views.CategoryVideosFeed))),
    url(r'', include(make_patterns(r'author/(\d+)', 'localtv_feeds_author',
                                    views.AuthorVideosFeed))),
    url(r'', include(make_patterns(r'videos-imported-from/(\d+)',
                                    'localtv_feeds_feed',
                                    views.FeedVideosFeed))),
    url(r'', include(make_patterns(r'tag/(.+)', 'localtv_feeds_tag',
                                    views.TagVideosFeed))),
    url(r'', include(make_patterns(r'search/(.+)', 'localtv_feeds_search',
                                    views.SearchVideosFeed))),
    url(r'', include(make_patterns(r'playlist/(\d+)', 'localtv_feeds_playlist',
                                    views.PlaylistVideosFeed))),
)

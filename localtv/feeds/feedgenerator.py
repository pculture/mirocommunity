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

from django.utils import feedgenerator, simplejson


class ThumbnailFeedGenerator(feedgenerator.Atom1Feed):
    def add_root_elements(self, handler):
        # First. let the superclass add its own essential root elements.
        super(ThumbnailFeedGenerator, self).add_root_elements(handler)

        # Second, add the necessary information for this feed to be identified
        # as an OpenSearch feed.
        if hasattr(self, 'opensearch_data'):
            for key in self.opensearch_data:
                name = 'opensearch:' + key
                value = unicode(self.opensearch_data[key])
                handler.addQuickElement(name, value)

    def root_attributes(self):
        attrs = feedgenerator.Atom1Feed.root_attributes(self)
        attrs['xmlns:media'] = 'http://search.yahoo.com/mrss/'
        attrs['xmlns:opensearch'] = 'http://a9.com/-/spec/opensearch/1.1/'
        return attrs

    def add_item_elements(self, handler, item):
        feedgenerator.Atom1Feed.add_item_elements(self, handler, item)
        if 'thumbnail' in item:
            handler.addQuickElement('media:thumbnail',
                                    attrs={'url': item['thumbnail']})
        if 'website_url' in item:
            handler.addQuickElement('link', attrs={
                    'rel': 'via',
                    'href': item['website_url']})
        if 'embed_code' in item or 'website_url' in item:
            handler.startElement('media:player',
                                 {'url': item.get('website_url', '')})
            handler.characters(item.get('embed_code', ''))
            handler.endElement('media:player')

class JSONGenerator(feedgenerator.SyndicationFeed):
    mime_type = 'application/json'
    def write(self, outfile, encoding):
        json = {}
        self.add_root_elements(json)
        self.write_items(json)
        simplejson.dump(json, outfile, encoding=encoding)

    def add_root_elements(self, json):
        json['title'] = self.feed['title']
        json['link'] = self.feed['link']
        json['id'] = self.feed['id']
        json['updated'] = unicode(self.latest_post_date())

    def write_items(self, json):
        json['items'] = []
        for item in self.items:
            self.add_item_elements(json['items'], item)

    def add_item_elements(self, json_items, item):
        json_item = {}
        json_item['title'] = item['title']
        json_item['link'] = item['link']
        json_item['when'] = item['when']
        if item.get('pubdate'):
            json_item['pubdate'] = unicode(item['pubdate'])
        if item.get('description'):
            json_item['description'] = item['description']
        if item.get('enclosure'):
            enclosure = item['enclosure']
            json_item['enclosure'] = {
                'link': enclosure.url,
                'length': enclosure.length,
                'type': enclosure.mime_type}
        if item['categories']:
            json_item['categories'] = item['categories']
        if 'thumbnail' in item:
            json_item['thumbnail'] = item['thumbnail']
            json_item['thumbnails_resized'] = resized = []
            for size, url in item['thumbnails_resized'].items():
                resized.append({'width': size[0],
                                'height': size[1],
                                'url': url})
        if 'website_url' in item:
            json_item['website_url'] = item['website_url']
        if 'embed_code' in item:
            json_item['embed_code'] = item['embed_code']

        json_items.append(json_item)

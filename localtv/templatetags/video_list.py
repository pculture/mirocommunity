# This file is part of Miro Community.
# Copyright (C) 2010 Participatory Culture Foundation
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

from django import template
from django.utils.functional import curry

from localtv.search.forms import VideoSearchForm
from localtv.search.utils import SortFilterMixin


register = template.Library()


class BaseVideoListNode(template.Node, SortFilterMixin):
    """
    Base helper class (abstract) for handling the get_video_list_* template
    tags.  Based heavily on the template tags for django.contrib.comments.

    Syntax::

        {% get_video_list_FOO as <varname> %}
        {% get_video_list_for_FOO <foo_instance> as <varname> %}

    """
    form_class = VideoSearchForm
    takes_argument = False # if True, takes an argument (tag/category/user
                           # lists)

    sort = None
    search_filter = None
    field_name = None

    @classmethod
    def handle_token(cls, parser, token):
        """Class method to parse get_video_list_* and return a Node."""
        bits = token.split_contents()
        tag_name = bits[0]
        bits = bits[1:]
        argument_count = int(cls.takes_argument) + 2
        if len(bits) != argument_count:
            raise template.TemplateSyntaxError(
                "%r tag requires %i arguments" % (tag_name, argument_count))
        item = None
        if cls.takes_argument:
            item = parser.compile_filter(bits[1])
            bits = bits[1:]
        if bits[0] != 'as':
            raise template.TemplateSyntaxError(
                    "%s argument in %r tag must be 'as'" % (
                        "Third" if cls.takes_argument else "Second", tag_name))
        return cls(item=item, as_varname=bits[1])

    def __init__(self, item=None, as_varname=None):
        self.item = item
        self.as_varname = as_varname

    def render(self, context):
        context[self.as_varname] = self.get_video_list(context)
        return ''

    def get_video_list(self, context):
        sqs = self._query("")
        sqs = self._sort(sqs, self.sort)
        if self.search_filter is not None:
            filter_dict = self.filters.get(self.search_filter, None)
            kwargs = {}
            if filter_dict is not None:
                item = self.item.resolve(context)
                if isinstance(item, filter_dict['model']):
                    kwargs['filter_objects'] = [item]
                elif isinstance(item, basestring):
                    kwargs[self.field_name] = item
                sqs, filter_obj = self._filter(sqs, self.search_filter,
                                   **kwargs)
        sqs.load_all()
        return [result.object for result in sqs]


class NewVideoListNode(BaseVideoListNode):
    """
    Insert a list of new videos into the context.

    """
    sort = '-date'


class PopularVideoListNode(BaseVideoListNode):
    """
    Insert a list of popular videos into the context.

    """
    sort = '-popular'


class FeaturedVideoListNode(BaseVideoListNode):
    """
    Insert a list of featured videos into the context.

    """
    sort = '-featured'


class CategoryVideoListNode(BaseVideoListNode):
    """
    Insert a list of videos for the given category into the context.

    """
    takes_argument = True
    search_filter = 'category'
    field_name = 'slug'
    sort = '-date'


class TagVideoListNode(BaseVideoListNode):
    """
    Insert a list of videos for the given tag into the context.

    """
    takes_argument = True
    search_filter = 'tag'
    field_name = 'name'


class UserVideoListNode(BaseVideoListNode):
    """
    Insert a list of videos for the given user into the context.

    """
    takes_argument = True
    search_filter = 'author'
    field_name = 'username'


register.tag('get_video_list_new', NewVideoListNode.handle_token)
register.tag('get_video_list_popular', PopularVideoListNode.handle_token)
register.tag('get_video_list_featured', FeaturedVideoListNode.handle_token)
register.tag('get_video_list_for_category', CategoryVideoListNode.handle_token)
register.tag('get_video_list_for_tag', TagVideoListNode.handle_token)
register.tag('get_video_list_for_user', UserVideoListNode.handle_token)

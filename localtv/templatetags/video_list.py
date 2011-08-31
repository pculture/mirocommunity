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
from localtv.search.util import SortFilterMixin


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

    @classmethod
    def handle_token(cls, parser, token):
        """Class method to parse get_video_list_* and return a Node."""
        tokens = token.split_contents()
        argument_count = int(cls.takes_argument) + 3
        if len(tokens) != argument_count:
            raise template.TemplateSyntaxError(
                "%r tag requires %i arguments" % (tokens[0], argument_count))
        if not cls.takes_argument:
            # {% get_whatever as varname %}
            if tokens[1] != 'as':
                raise template.TemplateSyntaxError(
                    "Second argument in %r tag must be 'as'" % tokens[0])
            return cls(as_varname=tokens[2])
        else:
            if tokens[2] != 'as':
                raise template.TemplateSyntaxError(
                    "Third argument in %r tag must be 'as'" % tokens[0])
            return cls(item=tokens[1], as_varname=tokens[3])

    def __init__(self, item=None, as_varname=None):
        if item is not None:
            if item.startswith('"') and item.endswith('"'):
                self.item = item[1:-1]
            elif item.startswith("'") and item.endswith("'"):
                self.item = item[1:-1]
            else:
                self.item = template.Variable(item)
        else:
            self.item = item
        self.as_varname = as_varname

    def render(self, context):
        context[self.as_varname] = self.get_video_list(context)
        return ''

    def get_video_list(self, context):
        sqs = self._query("")
        sqs = self._sort(sqs, self.sort)
        if self.search_filter is not None:
            sqs, filter_obj = self._filter(sqs, self.search_filter, context)
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


class FilteredVideoListNode(BaseVideoListNode):
    """
    Base class for filtered video lists.

    """
    takes_argument = True
    #: The name of the field which should be queried to fetch the instance
    #: to use in filtering if the passed-in value is a string.
    field_name = None

    def _filter(self, searchqueryset, search_filter, context):
        search_filter = self.filters.get(search_filter, None)
        if search_filter is not None:
            context = kwargs.pop('context', {})
            item = self.item.resolve(context)

            model_class = search_filter['model']
            super_filter = curry(super(FilteredVideoListNode, self)._filter,
                                    searchqueryset, search_filter)
            if isinstance(item, model_class):
                return super_filter(filter_obj=item)
            elif isinstance(item, basestring):
                try:
                    return super_filter(**{self.field_name: item})
                except model_class.DoesNotExist:
                    pass
            searchqueryset = searchqueryset.none()
        return searchqueryset, None


class CategoryVideoListNode(FilteredVideoListNode):
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

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

import datetime

from django import template
from django.contrib.auth.models import User
from django.db.models import Q

from tagging.models import Tag

from localtv.models import Video, Category, SiteLocation
from localtv.views import get_request_videos, get_popular_videos, get_featured_videos, get_latest_videos, get_tag_videos, get_author_videos, get_category_videos


register = template.Library()


class BaseVideoListNode(template.Node):
    """
    Base helper class (abstract) for handling the get_video_list_* template
    tags.  Based heavily on the template tags for django.contrib.comments.
    
    """

    takes_argument = False # if True, takes an argument (tag/category/user
                           # lists)

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
        context[self.as_varname] = self.get_query_set(context)
        return ''

    def get_query_set(self, context):
        raise NotImplementedError


class NewVideoListNode(BaseVideoListNode):
    """
    Insert a list of new videos into the context.
    
    """
    def get_query_set(self, context):
        return get_latest_videos(context['request'])


class PopularVideoListNode(BaseVideoListNode):
    """
    Insert a list of popular videos into the context.
    
    """
    def get_query_set(self, context):
        return get_popular_videos(context['request'])


class FeaturedVideoListNode(BaseVideoListNode):
    """
    Insert a list of featured videos into the context.
    
    """
    def get_query_set(self, context):
        return get_featured_videos(context['request'])


class CategoryVideoListNode(BaseVideoListNode):
    """
    Insert a list of videos for the given category into the context. Does not
    include videos that belong to that category's descendants.
    
    """
    takes_argument = True

    def get_query_set(self, context):
        category = self.item.resolve(context)
        request = context['request']
        if isinstance(category, basestring):
            try:
                category = Category.objects.get(
                    slug=category,
                    site=SiteLocation.objects.get_current().site
                )
            except Category.DoesNotExist:
                return Video.objects.none()
        elif not isinstance(category, Category):
            return Video.objects.none()
        return get_latest_videos(request).filter(
            categories=category
        ).distinct().order_by('-best_date')


class TagVideoListNode(BaseVideoListNode):
    """
    Insert a list of videos for the given tag into the context.
    
    """
    takes_argument = True

    def get_query_set(self, context):
        request = context['request']
        tag = self.item.resove(context)
        if isinstance(tag, basestring):
            try:
                tag = Tag.objects.get(name=tag)
            except Tag.DoesNotExist:
                return Video.objects.none()
        elif not isinstance(tag, Tag):
            return Video.objects.none()
        return get_tag_videos(request, tag)


class UserVideoListNode(BaseVideoListNode):
    """
    Insert a list of videos for the given user into the context.
    """
    takes_argument = True

    def get_query_set(self, context):
        request = context['request']
        author = self.item.resolve(context)
        if isinstance(author, basestring):
            try:
                author = User.objects.get(username=self.item)
            except User.DoesNotExist:
                return Video.objects.none()
        elif not isinstance(author, User):
            return Video.objects.none()
        return get_author_videos(request, author)


register.tag('get_video_list_new', NewVideoListNode.handle_token)
register.tag('get_video_list_popular', PopularVideoListNode.handle_token)
register.tag('get_video_list_featured', FeaturedVideoListNode.handle_token)
register.tag('get_video_list_for_category', CategoryVideoListNode.handle_token)
register.tag('get_video_list_for_tag', TagVideoListNode.handle_token)
register.tag('get_video_list_for_user', UserVideoListNode.handle_token)

from django import template

from localtv.search.utils import NormalizedVideoList
from localtv.search.views import SortFilterMixin


register = template.Library()


class BaseVideoListNode(SortFilterMixin, template.Node):
    """
    Base helper class (abstract) for handling the get_video_list_* template
    tags.  Based heavily on the template tags for django.contrib.comments.

    Syntax::

        {% get_video_list_FOO as <varname> %}
        {% get_video_list_for_FOO <foo_instance> as <varname> %}

    """

    @classmethod
    def handle_token(cls, parser, token):
        """Class method to parse get_video_list_* and return a Node."""
        bits = token.split_contents()
        tag_name = bits[0]
        bits = bits[1:]
        argument_count = int(cls.filter_name is not None) + 2
        if len(bits) != argument_count:
            raise template.TemplateSyntaxError(
                "%r tag requires %i arguments" % (tag_name, argument_count))
        item = None
        if argument_count == 3:
            item = parser.compile_filter(bits[0])
            bits = bits[1:]
        if bits[0] != 'as':
            raise template.TemplateSyntaxError(
                    "%s argument in %r tag must be 'as'" % (
                        "Third" if argument_count == 3 else "Second", tag_name))
        return cls(item=item, as_varname=bits[1])

    def __init__(self, item=None, as_varname=None):
        self.item = item
        self.as_varname = as_varname

    def render(self, context):
        context[self.as_varname] = self.get_video_list(context)
        return ''

    def get_video_list(self, context):
        form = self.get_form(filter_value=self.get_filter_value(context))
        return NormalizedVideoList(form.search())

    def get_filter_value(self, context):
        if self.filter_name is None:
            return None
        return self.item.resolve(context)


class NewVideoListNode(BaseVideoListNode):
    """
    Insert a list of new videos into the context.

    """
    pass


class PopularVideoListNode(BaseVideoListNode):
    """
    Insert a list of popular videos into the context.

    """
    sort = 'popular'


class FeaturedVideoListNode(BaseVideoListNode):
    """
    Insert a list of featured videos into the context.

    """
    sort = 'featured'


class CategoryVideoListNode(BaseVideoListNode):
    """
    Insert a list of videos for the given category into the context.

    """
    filter_name = 'category'

    def get_filter_value(self, context):
        return [self.item.resolve(context)]


class TagVideoListNode(BaseVideoListNode):
    """
    Insert a list of videos for the given tag into the context.

    """
    filter_name = 'tag'


class UserVideoListNode(BaseVideoListNode):
    """
    Insert a list of videos for the given user into the context.

    """
    filter_name = 'author'


register.tag('get_video_list_new', NewVideoListNode.handle_token)
register.tag('get_video_list_popular', PopularVideoListNode.handle_token)
register.tag('get_video_list_featured', FeaturedVideoListNode.handle_token)
register.tag('get_video_list_for_category', CategoryVideoListNode.handle_token)
register.tag('get_video_list_for_tag', TagVideoListNode.handle_token)
register.tag('get_video_list_for_user', UserVideoListNode.handle_token)

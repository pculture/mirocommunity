from django import template
from django.contrib import comments
from django.contrib.sites.models import Site


Comment = comments.get_model()
register = template.Library()


class AuthorCommentsNode(template.Node):
    def __init__(self, obj, as_varname):
        self.obj = obj
        self.as_varname = as_varname

    def render(self, context):
        obj = self.obj.resolve(context)
        context[self.as_varname] = Comment.objects.filter(
                                        site=Site.objects.get_current(),
                                        user=obj.pk).reverse()
        return ''


@register.tag('get_author_comments')
def get_author_comments(parser, token):
    tokens = validate_tag_tokens(token)
    return AuthorCommentsNode(template.Variable(tokens[2]), tokens[4])


class AuthorCommentCountNode(template.Node):
    def __init__(self, obj, as_varname):
        self.obj = obj
        self.as_varname = as_varname

    def render(self, context):
        obj = self.obj.resolve(context)
        context[self.as_varname] = Comment.objects.filter(
                                        site=Site.objects.get_current(),
                                        user=obj.pk).count()
        return ''


@register.tag('get_author_comment_count')
def get_author_comment_count(parser, token):
    tokens = validate_tag_tokens(token)
    return AuthorCommentCountNode(template.Variable(tokens[2]), tokens[4])


def validate_tag_tokens(token):
    tokens = token.split_contents()
    if len(tokens) != 5:
        raise template.TemplateSyntaxError(
            "%r tag requires 5 arguments" % (tokens[0],))
    if tokens[1] != 'for':
        raise template.TemplateSyntaxError(
            "Second argument in %r tag must be 'for'" % tokens[0])
    if tokens[3] != 'as':
        raise template.TemplateSyntaxError(
            "Fourth argument in %r tag must be 'as'" % tokens[0])
    return tokens

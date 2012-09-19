from django import template
from django.contrib import comments
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site

Comment = comments.get_model()

register = template.Library()

class EditorsCommentNode(template.Node):

    def __init__(self, obj, as_varname):
        self.obj = obj
        self.as_varname = as_varname

    def render(self, context):
        obj = self.obj.resolve(context)
        content_type = ContentType.objects.get_for_model(obj)
        comments = Comment.objects.filter(
            site=Site.objects.get_current(),
            content_type=content_type,
            object_pk=unicode(obj.pk),
            flags__flag='editors comment')
        try:
            context[self.as_varname] = comments[0]
        except IndexError:
            context[self.as_varname] = None
        return ''

@register.tag('get_editors_comment')
def get_editors_comment(parser, token):
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
    return EditorsCommentNode(template.Variable(tokens[2]), tokens[4])

from django import template
from django.contrib.staticfiles.storage import staticfiles_storage

from daguerre.helpers import AdjustmentHelper, AdjustmentInfoDict


register = template.Library()


class ThumbnailNode(template.Node):
    """
    Essentially an implementation of daguerre's AdjustmentNode with a
    different interface, to maintain backwards compatibility with old
    localtv_thumbnail template tags.
    
    """
    
    def __init__(self, video, size, as_varname=None, absolute=False):
        self.asvar = as_varname
        self.absolute = absolute # ???
        self.video = video
        self.width, self.height = size
    
    def render(self, context):
        video = self.video.resolve(context)

        # Backwards-compat: livesearch should just use the thumbnail_url.
        if getattr(video, '_livesearch', False):
            info_dict = AdjustmentInfoDict({
                'width': self.width,
                'height': self.height,
                'url': video.thumbnail_url
            })
        else:
            storage_path = None

            if video.has_thumbnail:
                storage_path = video.thumbnail_path
            elif video.feed_id and video.feed.has_thumbnail:
                storage_path = video.feed.thumbnail_path
            elif video.search_id and video.search.has_thumbnail:
                storage_path = video.search.thumbnail_path

            kwargs = {
                'width': self.width,
                'height': self.height,
                'adjustment': 'fill'
            }

            helper = AdjustmentHelper(storage_path, **kwargs)
            info_dict = helper.info_dict()

            # localtv_thumbnail has always fallen back in the code.
            if not info_dict:
                info_dict = AdjustmentInfoDict({
                    'width': self.width,
                    'height': self.height,
                    'url': staticfiles_storage.url('localtv/images/default_vid.gif')
                })
        
        if self.asvar is not None:
            context[self.asvar] = info_dict
            return ''
        return info_dict


@register.tag('get_thumbnail_url')
def get_thumbnail_url(parser, token):
    tokens = token.split_contents()
    if len(tokens) not in (4, 5, 6, 7):
        raise template.TemplateSyntaxError(
            '%r tag requires 4, 5, 6 or 7 arguments' % (tokens[0],))
    absolute = (tokens[1] == 'absolute')
    if absolute:
        if len(tokens) not in (5, 7):
            raise template.TemplateSyntaxError(
                '%r absolute tag requires 5 or 7 arguments' % (tokens[0],))
    elif len(tokens) not in (4, 6):
            raise template.TemplateSyntaxError(
                '%r tag requires 4 or 6 arguments' % (tokens[0],))        
    try:
        width = int(tokens[2 + absolute])
        height = int(tokens[3 + absolute])
    except ValueError:
        raise template.TemplateSyntaxError(
            'Third and forth arguments in %r tag must be integers' % (
                tokens[0],))
    video = template.Variable(tokens[1 + absolute])
    if len(tokens) == (6 + absolute): # get_thumbnail_url video width height as
                                    # variable
        if tokens[4 + absolute] != 'as':
            raise template.TemplateSyntaxError(
                "Fifth argument in %r tag must be 'as'" % tokens[0])
        return ThumbnailNode(video, (width, height), tokens[5 + absolute],
                             absolute=absolute)
    else:
        return ThumbnailNode(video, (width, height),
                             absolute=absolute)

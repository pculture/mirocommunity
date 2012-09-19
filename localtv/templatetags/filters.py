import datetime
import re

from bs4 import BeautifulSoup, Comment
from django.contrib.contenttypes.models import ContentType
from django.template import Library
from django.utils.html import urlize
from django.utils.safestring import mark_safe
import lxml.html
from tagging.models import Tag


register = Library()


@register.filter
def simpletimesince(value, arg=None):
    """Formats a date as the time since that date (i.e. "4 days, 6 hours")."""
    from django.utils.timesince import timesince
    if not value:
        return u''
    try:
        if arg:
            return timesince(value, arg)
        return timesince(value, datetime.datetime.utcnow()).split(', ')[0]
    except (ValueError, TypeError):
        return u''


@register.filter
def sanitize(value, extra_filters=None):
    """
    Sanitize the given HTML.

    Based on code from:
    * http://www.djangosnippets.org/snippets/1655/
    * http://www.djangosnippets.org/snippets/205/
    """
    if value is None:
        return u''

    if '<' not in value and '&#' not in value and \
            re.search(r'&\w+;', value) is None: # no HTML
        # convert plain-text links into HTML
        return mark_safe(urlize(value,
                                nofollow=True,
                                autoescape=True).replace('\n', '<br/>'))

    js_regex = re.compile(r'[\s]*(&#x.{1,7})?'.join(list('javascript')),
                          re.IGNORECASE)
    allowed_tags = ('p i strong em b u a h1 h2 h3 h4 h5 h6 pre br img ul '
                    'ol li span').split()
    allowed_attributes = 'href src style'.split()

    whitelist = False
    extra_tags = ()
    extra_attributes = ()
    if isinstance(extra_filters, basestring):
        if '|' in extra_filters:
            parts = extra_filters.split('|')
        else:
            parts = [extra_filters.split()]
        if parts[0] == 'whitelist':
            whitelist = True
            parts = parts[1:]
        extra_tags = parts[0].split()
        if len(parts) > 1:
            extra_attributes = parts[1].split()
    elif extra_filters:
        extra_tags = extra_filters

    if whitelist:
        allowed_tags, allowed_attributes = extra_tags, extra_attributes
    else:
        allowed_tags = set(allowed_tags) - set(extra_tags)
        allowed_attributes = set(allowed_attributes) - set(extra_attributes)

    soup = BeautifulSoup(value)
    for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
        # remove comments
        comment.extract()

    for tag in soup.find_all(True):
        if tag.name not in allowed_tags:
            tag.hidden = True
        else:
            tag.attrs = dict((key, js_regex.sub('', val))
                             for key, val in tag.attrs.iteritems()
                             if key in allowed_attributes)

    return mark_safe(unicode(soup))


@register.filter
def wmode_transparent(value):
    doc = lxml.html.fromstring('<div>' + value + '</div>')
    # Find any object tag
    tags = doc.cssselect('object')
    for object_tag in tags:
        WMODE_TRANSPARENT_PARAM = lxml.html.fragment_fromstring("""<param name="wmode" value="transparent"></param>""")
        object_tag.insert(0, WMODE_TRANSPARENT_PARAM)

    # Find any relevant flash embed
    embeds = doc.cssselect('embed')
    for embed in embeds:
        if embed.get('type') == 'application/x-shockwave-flash':
            embed.set('wmode', 'transparent')

    wrapped_in_a_div = lxml.html.tostring(doc)
    if (wrapped_in_a_div.startswith('<div>') and 
        wrapped_in_a_div.endswith('</div>')):
        start = len('<div>')
        end = - len('</div>')
        return mark_safe(wrapped_in_a_div[start:end])
    # else, uh, return the wrapped thing.
    return mark_safe(wrapped_in_a_div)


@register.filter
def same_db_tags(video):
    """
    Given a video, renders a string containing that video's tags, guaranteed
    to be from the same database as the original. This is part of the
    CELERY_USING hack and will be eliminated without warning.

    """
    from localtv.models import Video
    if not isinstance(video, Video):
        return u''
    using = video._state.db
    ct = ContentType.objects.db_manager(using).get_for_model(video)
    tags = Tag.objects.using(using).filter(items__content_type__pk=ct.pk,
                                           items__object_id=video.pk)
    return u'\n'.join([unicode(t) for t in tags])

import re
from BeautifulSoup import BeautifulSoup, Comment, Tag
from django.template import Library
from django.utils.safestring import mark_safe

register = Library()

def simpletimesince(value, arg=None):
    """Formats a date as the time since that date (i.e. "4 days, 6 hours")."""
    from django.utils.timesince import timesince
    if not value:
        return u''
    try:
        if arg:
            return timesince(value, arg)
        return timesince(value).split(', ')[0]
    except (ValueError, TypeError):
        return u''

def sanitize(value, extra_filters=None):
    """
    Sanitize the given HTML.

    Based on code from:
    * http://www.djangosnippets.org/snippets/1655/
    * http://www.djangosnippets.org/snippets/205/
    """
    if value is None:
        return u''
    
    js_regex = re.compile(r'[\s]*(&#x.{1,7})?'.join(list('javascript')),
                          re.IGNORECASE)
    allowed_tags = 'p i strong em b u a h1 h2 h3 h4 h5 h6 pre br img'.split()
    allowed_attributes = 'href src'.split()

    soup = BeautifulSoup(value)
    for comment in soup.findAll(text=lambda text: isinstance(text, Comment)):
        # remove comments
        comment.extract()

    for tag in soup.findAll(True):
        if tag.name not in allowed_tags:
            tag.hidden = True
        elif extra_filters and tag.name in extra_filters:
            tag.hidden = True
        else:
            tag.attrs = [(attr, js_regex.sub('', val))
                         for attr, val in tag.attrs
                         if attr in allowed_attributes]

    return mark_safe(soup.renderContents().decode('utf8'))


def wmode_transparent(value):
    soup = BeautifulSoup(value)
    param_tag = Tag(soup, 'param', [
            ('name', 'wmode'),
            ('value', 'transparent')])

    for html_object in soup.findAll('object'):
        html_object.insert(0, param_tag)

    for flash_embed in soup.findAll('embed',
                                type="application/x-shockwave-flash"):
        flash_embed['wmode'] = 'transparent'

    return mark_safe(soup.prettify())

register.filter(simpletimesince)
register.filter(sanitize)
register.filter(wmode_transparent)

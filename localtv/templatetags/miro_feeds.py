from django import template
from django.core.urlresolvers import reverse


register = template.Library()

MIRO_SUBSCRIBE_BASE = 'http://subscribe.getmiro.com/'
#'http://subscribe.getmiro.com/?url1=http%3A//podcast.cnbc.com/mmpodcast/suzeormanshow.xml&trackback1=https%3A//www.miroguide.com/feeds/10063/subscribe-hit

def subscribify_url(url):
    pass


@register.simple_tag
def reversible_miro_subscribe_feed(reversible_url):
    actual_url = reverse(reversible_url)

import hashlib

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.http import Http404
from django.utils.translation import ugettext as _

from localtv.feeds.views import BaseVideosFeed
from localtv.models import Video


def generate_secret():
    sha = hashlib.sha1(settings.DATABASES['default']['NAME'])
    sha.update('admin_feed')
    sha.update(str(settings.SITE_ID))
    sha.update(settings.SECRET_KEY)
    return sha.hexdigest()[:16]


def verify_secret(func):
    def wrapper(request, secret):
        if secret != generate_secret():
            raise Http404
        return func(request)
    return wrapper


class UnapprovedVideosFeed(BaseVideosFeed):
    def link(self):
        return reverse('localtv_admin_approve_reject')

    def title(self):
        return "%s: %s" % (
            Site.objects.get_current().name, _('Videos Awaiting Moderation'))

    def items(self, obj):
        items = Video.objects.filter(
            status=Video.UNAPPROVED,
            site=Site.objects.get_current()
        ).order_by(
            'when_submitted', 'when_published'
        )
        items = self._opensearch_items(items, obj)
        return self._bulk_adjusted_items(items)


class UnapprovedUserVideosFeed(UnapprovedVideosFeed):
    def title(self):
        return "%s: %s" % (
            Site.objects.get_current().name, _('Unapproved User Submissions'))

    def items(self, obj):
        items = Video.objects.filter(
            status=Video.UNAPPROVED,
            site=Site.objects.get_current(),
            feed=None,
            search=None
        ).order_by(
            'when_submitted', 'when_published'
        )
        items = self._opensearch_items(items, obj)
        return self._bulk_adjusted_items(items)


unapproved = verify_secret(UnapprovedVideosFeed())
unapproved_user = verify_secret(UnapprovedUserVideosFeed())

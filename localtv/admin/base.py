# Copyright 2009 - Participatory Culture Foundation
# 
# This file is part of Miro Community.
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

from django.conf import settings
from django.conf.urls.defaults import url, patterns, include
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.datastructures import SortedDict


ADMIN_ROOT_VIEW = getattr(settings, 'LOCALTV_ADMIN_ROOT_VIEW', None)


class RegistrationError(Exception):
    pass


class MiroCommunityAdminSection(object):
    #: The url (beyond ``/admin/``) for this section. For example, a section at
    #: ``/admin/moderation/`` would have a ``url_prefix`` of ``moderation/``
    url_prefix = None

    #: The text which will be displayed for this section in the navigation.
    navigation_text = None

    #: URL patterns for this section.
    urlpatterns = None

    #: An tuple containing at least one ``(verbose_name, url_reverse_name)``
    #: tuple.
    pages = ()

    #: Whether the section should only be displayed to admins for the current
    #: site. Note that this does not affect who can *access* the views supplied
    #: by the section. Restricted access must be handled by the views.
    site_admin_required = False


class MiroCommunitySectionRegistry(object):
    def __init__(self):
        self._registry = SortedDict()

    def register(self, section_class):
        if section_class.url_prefix in self._registry:
            raise RegistrationError("Another section is already registered for "
                            "the url prefix '%s'" % section_class.url_prefix)
        self._registry[section_class.url_prefix] = section_class()

    def unregister(self, section_class):
        url_prefix = section_class.url_prefix
        if (url_prefix in self._registry and
            isinstance(self._registry[url_prefix], section_class)):
            del self._registry[url_prefix]

    def get_urlpatterns(self):
        urlpatterns = patterns('',
            url(r'^$', self.root_view, name='localtv_admin_root')
        )

        for url_prefix, section in self._registry.iteritems():
            urlpatterns += patterns('',
                url(r'^%s/' % url_prefix, include(section.urlpatterns))
            )
        return urlpatterns

    def root_view(self, request):
        view = (ADMIN_ROOT_VIEW if ADMIN_ROOT_VIEW is not None
                else 'localtv_admin_dashboard')
        return HttpResponseRedirect(reverse(view))



registry = MiroCommunitySectionRegistry()
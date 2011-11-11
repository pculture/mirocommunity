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
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.template.defaultfilters import slugify, capfirst
from django.utils.datastructures import SortedDict

from localtv.admin.views import (MiroCommunityAdminListView,
                                 MiroCommunityAdminCreateView,
                                 MiroCommunityAdminUpdateView,
                                 MiroCommunityAdminDeleteView)


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


class CRUDSection(MiroCommunityAdminSection):
    #: The model which is handled by this section.
    model = None

    #: A queryset of objects for this section.
    queryset = None

    paginate_by = None

    site_admin_required = True

    list_view_class = MiroCommunityAdminListView
    create_view_class = MiroCommunityAdminCreateView
    update_view_class = MiroCommunityAdminUpdateView
    delete_view_class = MiroCommunityAdminDeleteView

    list_view_name = 'localtv_admin_%(model_name)s_list'
    create_view_name = 'localtv_admin_%(model_name)s_create'
    update_view_name = 'localtv_admin_%(model_name)s_update'
    delete_view_name = 'localtv_admin_%(model_name)s_delete'

    create_form_class = None
    update_form_class = None

    template_prefixes = (
        'localtv/admin/',
    )

    @property
    def navigation_text(self):
        return capfirst(self.get_model_class()._meta.verbose_name_plural)

    @property
    def url_prefix(self):
        return slugify(self.get_model_class()._meta.verbose_name_plural)

    def get_model_class(self):
        if self.model is not None:
            return self.model
        else:
            return self.get_queryset().model

    def get_queryset(self):
        if self.queryset is not None:
            return self.queryset
        elif self.model is not None:
            return self.model._default_manager.all()
        else:
            raise ImproperlyConfigured

    def get_template_names(self, step):
        return [
            '%s%s.html' % (prefix, step) for prefix in self.template_prefixes
        ]

    def get_view_names(self):
        model = self.get_model_class()
        info = {
            'model_name': model._meta.module_name,
            'app_label': model._meta.app_label
        }
        return {
            'list_view_name': self.list_view_name % info,
            'create_view_name': self.create_view_name % info,
            'update_view_name': self.update_view_name % info,
            'delete_view_name': self.delete_view_name % info,
        }


    def get_view_kwargs(self):
        return self.get_view_names()

    def get_list_view_kwargs(self):
        kwargs = self.get_view_kwargs()
        kwargs.update({
            'template_name': self.get_template_names('list'),
            'queryset': self.get_queryset(),
            'paginate_by': self.paginate_by
        })
        return kwargs

    def get_create_view_kwargs(self):
        kwargs = self.get_view_kwargs()
        kwargs.update({
            'model': self.get_model_class(),
            'template_name': self.get_template_names('create'),
            'form_class': self.create_form_class
        })
        return kwargs

    def get_update_view_kwargs(self):
        kwargs = self.get_view_kwargs()
        kwargs.update({
            'queryset': self.get_queryset(),
            'template_name': self.get_template_names('update'),
            'form_class': self.update_form_class
        })
        return kwargs

    def get_delete_view_kwargs(self):
        kwargs = self.get_view_kwargs()
        kwargs.update({
            'queryset': self.get_queryset(),
            'template_name': self.get_template_names('delete')
        })
        return kwargs

    def get_list_view(self):
        return self.list_view_class.as_view(**self.get_list_view_kwargs())

    def get_create_view(self):
        return self.create_view_class.as_view(**self.get_create_view_kwargs())

    def get_update_view(self):
        return self.update_view_class.as_view(**self.get_update_view_kwargs())

    def get_delete_view(self):
        return self.delete_view_class.as_view(**self.get_delete_view_kwargs())

    @property
    def urlpatterns(self):
        view_names = self.get_view_names()

        urlpatterns = patterns('',
            url(r'^$', self.get_list_view(),
                name=view_names['list_view_name']),
            url(r'^add/$', self.get_create_view(),
                name=view_names['create_view_name']),
            url(r'^(?P<pk>\d+)/$', self.get_update_view(),
                name=view_names['update_view_name']),
            url(r'^(?P<pk>\d+)/delete/$', self.get_delete_view(),
                name=view_names['delete_view_name'])
        )
        return urlpatterns

    @property
    def pages(self):
        view_names = self.get_view_names()
        return (
            (self.navigation_text, view_names['list_view_name']),
        )



class MiroCommunitySectionRegistry(object):
    def __init__(self):
        self._registry = SortedDict()

    def register(self, section_class):
        section = section_class()
        url_prefix = section.url_prefix
        if url_prefix in self._registry:
            raise RegistrationError("Another section is already registered for "
                            "the url prefix '%s'" % url_prefix)
        self._registry[url_prefix] = section

    def unregister(self, section_class):
        section = section_class()
        url_prefix = section.url_prefix
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
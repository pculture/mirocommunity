# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2010, 2011, 2012 Participatory Culture Foundation
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

from django import forms
from django.forms.models import modelformset_factory, BaseModelFormSet
from django.forms.models import inlineformset_factory, BaseInlineFormSet

from localtv.playlists import models
from localtv.admin.forms import BulkFormSetMixin

class PlaylistForm(forms.ModelForm):
    class Meta:
        model = models.Playlist
        fields = ['name', 'slug', 'description']

    def _clean_unique(self, field):
        """
        Make sure that the given field is unique.
        """
        value = self.cleaned_data[field]
        if getattr(self.instance, field, None) == value:
            # not modified
            return value
        if models.Playlist.objects.filter(**{
                field: value,
                'user': self.instance.user}).count():
            raise forms.ValidationError(
                "A playlist with that %s already exists" % field)
        return value

    def clean_name(self):
        return self._clean_unique('name')

    def clean_slug(self):
        return self._clean_unique('slug')


class BasePlaylistFormSet(BulkFormSetMixin, BaseModelFormSet):
    pass

PlaylistFormSet = modelformset_factory(models.Playlist,
                                       formset=BasePlaylistFormSet,
                                       exclude=['name', 'description', 'slug',
                                                'user', 'items', 'status',
                                                'site'],
                                       extra=0,
                                       can_delete=True)
# just used for the ordering
class BasePlaylistItemFormSet(BulkFormSetMixin, BaseInlineFormSet):
    def _get_ordered_forms(self):
        """
        Based on Django's _get_ordered_forms, but gives precedence to the order
        which changed more.

        For example, if two videos both get changed to the 3 spot, the video
        which had the most-different previous order gets it.
        """
        if not self.is_valid() or not self.can_order:
            raise AttributeError(
                "'%s' object has no attribute 'ordered_forms'" %
                self.__class__.__name__)
        if not hasattr(self, '_ordering'):
            self._ordering = []
            for i in range(0, self.total_form_count()):
                form = self.forms[i]
                if self.can_delete and self._should_delete_form(form):
                    continue
                # add 1 to the ordering because 'ORDER' is 1-indexed
                self._ordering.append((i + 1, form.cleaned_data['ORDER']))
            def compare_ordering_values(x, y):
                if x[1] is None:
                    return 1
                if y[1] is None:
                    return -1
                if x[1] == y[1]: # same order, give precendence to the one that
                                 # changed more
                    return (x[1] - x[0]) - (y[1] - y[0])
                return x[1] - y[1]
            self._ordering.sort(compare_ordering_values)
        return [self.forms[i[0]-1] for i in self._ordering]
    ordered_forms = property(_get_ordered_forms)

    def save(self, **kwargs):
        for form in self.deleted_forms:
            form.instance.delete()
        self.instance.set_playlistitem_order(
            [form.instance.pk for form in self.ordered_forms])

PlaylistItemFormSet = inlineformset_factory(models.Playlist,
                                            models.PlaylistItem,
                                            formset=BasePlaylistItemFormSet,
                                            exclude=['video'],
                                            extra=0,
                                            can_delete=True,
                                            can_order=True)

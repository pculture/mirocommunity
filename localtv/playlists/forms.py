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
                                                'user', 'items'],
                                       extra=0,
                                       can_delete=True)
# just used for the ordering
class BasePlaylistItemFormSet(BulkFormSetMixin, BaseInlineFormSet):
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

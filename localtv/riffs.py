from djam.riffs.models import ModelRiff
import floppyforms as forms
from haystack import connections
from tagging.forms import TagField

from localtv.models import Video


class VideoForm(forms.ModelForm):
    tags = TagField(required=False)

    def save(self, commit=True):
        # We need to update the Video.tags descriptor manually because
        # Django's model forms does not (django.forms.models.construct_instance)
        self.instance.tags = self.cleaned_data['tags']
        instance = super(VideoForm, self).save(commit=False)
        if commit:
            instance.save(update_index=False)
            self.save_m2m()
            instance._update_index = True
            ui = connections['default'].get_unified_index()
            ui.get_index(Video)._enqueue_update(instance)
        return instance


class VideoRiff(ModelRiff):
    model = Video
    list_kwargs = {
        'paginate_by': 10,
        'filters': ('status',),
    }
    update_kwargs = {
        'form_class': VideoForm,
        'fieldsets': (
            (None, {
                'fields': (
                    'name',
                    'website_url',
                    'thumbnail',
                    'when_published',
                    'description',
                    'embed_code',
                    'tags',
                    'categories',
                    'authors',
                )
            }),
        ),
    }


riffs = [VideoRiff]

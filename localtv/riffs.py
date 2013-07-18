from djam.riffs.models import ModelRiff
from django.conf import settings
from django.db.models import Count
from django.template.defaultfilters import pluralize
import floppyforms as forms
from haystack import connections
from tagging.forms import TagField

from localtv.models import Video, Feed, SourceImport
from localtv.tasks import feed_update
from localtv.templatetags.filters import simpletimesince


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


class FeedCreateForm(forms.ModelForm):
    def save(self, commit=True):
        self.instance.site_id = settings.SITE_ID
        self.instance.name = self.instance.original_url
        instance = super(FeedCreateForm, self).save(commit)
        if commit:
            feed_update.delay(instance.pk)
        return instance


def latest_import(source):
    try:
        latest = source.imports.latest()
    except SourceImport.DoesNotExist:
        return u"Waiting for import ({time})".format(
            time=simpletimesince(source.created_timestamp))
    if latest.is_complete:
        status = u"Finished {time} ago.".format(
            time=simpletimesince(latest.modified_timestamp))
    else:
        status = u"Updating..."

    results = []
    if latest.error_count:
        results.append(u"{0} error{1}.".format(latest.error_count,
                                              pluralize(latest.error_count)))

    if latest.import_count:
        results.append(u"{0} video{1} imported.".format(
            latest.import_count,
            pluralize(latest.import_count)))
    else:
        results.append(u"No new videos found.")

    return u"{0} {1}".format(status, u" ".join(results))
latest_import.do_not_call_in_templates = True


def video_count(source):
    return source.video_count
video_count.admin_order_field = 'video_count'
video_count.do_not_call_in_templates = True


class FeedRiff(ModelRiff):
    model = Feed
    list_kwargs = {
        'paginate_by': 10,
        'columns': ('name', 'original_url', video_count, latest_import),
        'queryset': Feed.objects.annotate(video_count=Count('video')),
    }
    create_kwargs = {
        'form_class': FeedCreateForm,
        'fieldsets': (
            (None, {
                'fields': (
                    'original_url',
                    'auto_categories',
                    'auto_authors',
                    'moderate_imported_videos',
                )
            }),
        ),
    }
    update_kwargs = {
        'fieldsets': (
            (None, {
                'fields': (
                    'original_url',
                    'auto_categories',
                    'auto_authors',
                    'moderate_imported_videos',
                    'disable_imports',
                )
            }),
            ('Metadata', {
                'fields': (
                    'name',
                    'external_url',
                    'description',
                )
            })
        ),
    }


riffs = [VideoRiff, FeedRiff]

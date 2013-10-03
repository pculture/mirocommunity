from djam.riffs.base import Riff
from djam.riffs.models import ModelRiff
from django.conf.urls import patterns, url
from django.db.models import Count
from django.template.defaultfilters import pluralize

from localtv.admin.forms import (VideoForm, FeedCreateForm, ProfileForm,
                                 NotificationsForm, SettingsForm,
                                 CategoryForm)
from localtv.admin.views import ProfileView, NotificationsView, SettingsView
from localtv.models import Video, Feed, SourceImport, Category
from localtv.templatetags.filters import simpletimesince


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


class NotificationsRiff(Riff):
    display_name = "Notifications"

    def get_extra_urls(self):
        return patterns('',
            url(r'^$',
                NotificationsView.as_view(
                    form_class=NotificationsForm,
                    template_name='djam/form.html',
                    **self.get_view_kwargs()),
                name='notifications'),
        )

    def get_default_url(self):
        return self.reverse('notifications')


class ProfileRiff(Riff):
    display_name = "Profile"

    def get_extra_urls(self):
        return patterns('',
            url(r'^$',
                ProfileView.as_view(
                    form_class=ProfileForm,
                    template_name='djam/form.html',
                    **self.get_view_kwargs()),
                name='profile'),
        )

    def get_default_url(self):
        return self.reverse('profile')


class SettingsRiff(Riff):
    display_name = "Settings"

    def get_extra_urls(self):
        return patterns('',
            url(r'^$',
                SettingsView.as_view(
                    form_class=SettingsForm,
                    template_name='djam/form.html',
                    **self.get_view_kwargs()),
                name='settings'),
        )

    def get_default_url(self):
        return self.reverse('settings')


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
                    'external_url',
                    'thumbnail',
                    'description',
                    'embed_code',
                    'tags',
                    'categories',
                    'authors',
                )
            }),
        ),
    }


class CategoryRiff(ModelRiff):
    model = Category
    list_kwargs = {
        'paginate_by': 10,
        'columns': ('name',)
    }
    update_kwargs = {
        'form_class': CategoryForm,
        'fieldsets': (
            (None, {
                'fields': (
                    'name',
                    'slug',
                    'logo',
                    'description',
                    'parent',
                )
            }),
        ),
    }

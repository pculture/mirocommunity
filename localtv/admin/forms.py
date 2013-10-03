# encoding: utf-8

from django.conf import settings
from django.contrib.auth.models import User
from django.utils.encoding import force_unicode
import floppyforms as forms
from haystack import connections
from notification import models as notification
from tagging.forms import TagField

from localtv.models import Video, SiteSettings
from localtv.tasks import feed_update
from localtv.utils import get_profile_model


Profile = get_profile_model()


class FeedCreateForm(forms.ModelForm):
    def save(self, commit=True):
        self.instance.site_id = settings.SITE_ID
        self.instance.name = self.instance.original_url
        instance = super(FeedCreateForm, self).save(commit)
        if commit:
            feed_update.delay(instance.pk)
        return instance


class NotificationsForm(forms.Form):
    CHOICES = (
        ('video_approved', 'A video you submitted was approved'),
        ('video_comment', 'Someone left a comment on your video'),
        ('comment_post_comment',
         'Someone left a comment on a video you commented on'),
    )
    ADMIN_CHOICES = (
        ('admin_new_comment', 'A new comment was left on the site'),
        ('admin_new_submission', 'A new video was submitted'),
        ('admin_new_playlist', 'A playlist requested to be public'),
        ('admin_video_updated',
         'The metadata of a video was updated on a remote site'),
        ('admin_queue_daily', 'A daily update of the review queue status'),
        ('admin_queue_weekly', 'A weekly update of the review queue status'),
    )

    notifications = forms.MultipleChoiceField(
        required=False, choices=CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label='Get notifications when…')

    def __init__(self, user, *args, **kwargs):
        self.instance = user
        forms.Form.__init__(self, *args, **kwargs)
        if self.instance:
            field = self.fields['notifications']
            site_settings = SiteSettings.objects.get_current()
            if site_settings.user_is_admin(self.instance):
                field.choices = self.CHOICES + self.ADMIN_CHOICES

            initial = []
            for choice, label in field.choices:
                notice_type = notification.NoticeType.objects.get(label=choice)
                if notification.should_send(self.instance, notice_type, "1"):
                    initial.append(choice)
            self.initial.setdefault('notifications', initial)

    def save(self):
        if not self.instance:
            raise RuntimeError('Cannot save the notifications without a user.')

        for choice, label in self.fields['notifications'].choices:
            notice_type = notification.NoticeType.objects.get(label=choice)
            setting = notification.get_notification_setting(self.instance,
                                                            notice_type, "1")
            setting.send = choice in self.cleaned_data['notifications']
            setting.save()
        return self.instance


class ProfileForm(forms.ModelForm):
    name = forms.CharField(max_length=61, required=False)
    location = forms.CharField(max_length=200, required=False)
    website = forms.URLField(required=False)
    logo = forms.ImageField(required=False,
                            label='Photo')
    description = forms.CharField(
        widget=forms.Textarea,
        required=False)

    class Meta:
        model = User
        fields = ['name', 'username', 'email', 'location', 'website', 'logo',
                  'description']

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        if self.instance.pk:  # existing user:
            self.fields['name'].initial = self.instance.get_full_name()
            try:
                profile = self.instance.get_profile()
            except Profile.DoesNotExist:
                pass  # we'll do it later
            else:
                for field_name in ('location', 'website', 'description', 'logo'):
                    self.fields[field_name].initial = getattr(profile,
                                                              field_name)

    def clean_name(self):
        if not self.cleaned_data['name']:
            return '', ''
        parts = self.cleaned_data['name'].split()
        first, parts = [parts[0]], parts[1:]
        while len(' '.join(parts)) > 30:
            first.append(parts[0])
            parts = parts[1:]
        if len(' '.join(first)) > 30:
            raise forms.ValidationError(
                'First and last name must be less than 30 characters.')
        return ' '.join(first), ' '.join(parts)

    def clean_username(self):
        username = self.cleaned_data['username']
        if username == force_unicode(self.instance.username):  # no change
            return username
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('That username is already taken.')
        return username

    def save(self, **kwargs):
        (self.instance.first_name,
         self.instance.last_name) = self.cleaned_data.get('name', ('', ''))
        instance = forms.ModelForm.save(self, **kwargs)

        def save_m2m():
            try:
                profile = instance.get_profile()
            except Profile.DoesNotExist:
                profile = Profile.objects.create(
                    user=instance)
            for field_name in ('location', 'website', 'logo', 'description'):
                value = self.cleaned_data.get(field_name)
                if value:
                    setattr(profile, field_name, value)
            profile.save()

        if hasattr(self, 'save_m2m'):
            old_m2m = self.save_m2m
            def _():
                save_m2m()
                old_m2m()
            self.save_m2m = _
        else:
            save_m2m()

        return instance


class SettingsForm(forms.ModelForm):
    name = forms.CharField(label='Site name', max_length=50)

    class Meta:
        model = SiteSettings
        fields = ('logo', 'logo_contains_site_name', 'background', 'css',
                  'footer_content', 'site_description', 'google_analytics_ua',
                  'google_analytics_domain', 'facebook_admins',
                  'submission_allowed', 'submission_requires_login',
                  'submission_requires_email')

    def save(self):
        settings = super(SettingsForm, self).save()
        settings.site.name = self.cleaned_data['name']
        settings.site.save()
        SiteSettings.objects.clear_cache()
        return settings


class VideoForm(forms.ModelForm):
    tags = TagField(required=False, widget=forms.widgets.Input)

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

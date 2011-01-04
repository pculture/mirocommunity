from django import forms
from django.contrib.auth.models import User
from django.utils.encoding import force_unicode

from localtv import models, util
from notification import models as notification

Profile = util.get_profile_model()

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
        if self.instance.pk: # existing user:
            self.fields['name'].initial = self.instance.get_full_name()
            try:
                profile = self.instance.get_profile()
            except Profile.DoesNotExist:
                pass # we'll do it later
            else:
                for field_name in ('location', 'website', 'description'):
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
        if username == force_unicode(self.instance.username): # no change
            return username
        if User.objects.filter(username=username).count():
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

class NotificationsForm(forms.Form):

    CHOICES = (
        ('video_approved', 'A video you submitted was approved'),
        ('video_comment', 'Someone left a comment on your video'),
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
        widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        forms.Form.__init__(self, *args, **kwargs)
        if self.instance:
            field = self.fields['notifications']
            sitelocation = models.SiteLocation.objects.get_current()
            if sitelocation.user_is_admin(self.instance):
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

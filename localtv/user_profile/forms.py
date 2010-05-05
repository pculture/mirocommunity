from django import forms
from django.contrib.auth.models import User

from localtv import models, util
from notification import models as notification

Profile = util.get_profile_model()

class ProfileForm(forms.ModelForm):
    name = forms.CharField(max_length=61)
    username = forms.CharField(max_length=30)
    email = forms.EmailField()

    class Meta:
        model = Profile
        fields = ['name', 'username', 'email', 'location', 'website', 'logo',
                  'description']

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        if instance is not None:
            initial = kwargs.setdefault('initial', {})
            initial.setdefault('username', instance.user.username)
            initial.setdefault('name', u'%s %s' % (instance.user.first_name,
                                                   instance.user.last_name))
            initial.setdefault('email', instance.user.email)
        forms.ModelForm.__init__(self, *args, **kwargs)

    def clean_name(self):
        parts = self.cleaned_data['name'].split()
        first, parts = [parts[0]], parts[1:]
        while len(' '.join(parts)) > 30:
            first.append(parts[0])
            parts = parts[1:]
        if len(' '.join(first)) > 30:
            raise forms.ValidationError(
                'First or last name must be less than 30 characters.')
        return ' '.join(first), ' '.join(parts)

    def clean_username(self):
        username = self.cleaned_data['username']
        if username == self.instance.user.username: # no change
            return username
        if User.objects.filter(username=username).count():
            raise forms.ValidationError('That username is already taken.')
        return username

    def save(self, **kwargs):
        (self.instance.user.first_name,
         self.instance.user.last_name) = self.cleaned_data['name']
        self.instance.user.username = self.cleaned_data['username']
        self.instance.user.email = self.cleaned_data['email']
        instance = forms.ModelForm.save(self, **kwargs)

        if hasattr(self, 'save_m2m'): # not committed
            old_save_m2m = self.save_m2m
            def save_m2m(self):
                instance.user.save()
                old_save_m2m()
            self.save_m2m = save_m2m
        else:
            instance.user.save()

        return instance

class NotificationsForm(forms.Form):

    CHOICES = (
        ('video_approved', 'A video you submitted was approved'),
        ('video_comment', 'Someone left a comment on your video'),
        )
    ADMIN_CHOICES = (
        ('admin_new_comment', 'A new comment was left on the site'),
        ('admin_new_submission', 'A new video was submitted'),
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

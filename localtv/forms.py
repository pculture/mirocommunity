import urllib2

from django import forms
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db.models import Q
import vidscraper
from vidscraper.exceptions import UnhandledVideo

from localtv.models import Video, SiteSettings
from localtv.settings import API_KEYS


class SubmitForm(forms.Form):
    """Accepts submission of a URL."""
    url = forms.URLField(verify_exists=False)
    submit_duplicate = forms.BooleanField(required=False)

    def __init__(self, request, *args, **kwargs):
        self.request = request
        super(SubmitForm, self).__init__(*args, **kwargs)

        if not request.user.is_authenticated():
            site_settings = SiteSettings.objects.get_current()
            if site_settings.submission_requires_email:
                self.fields['email'] = forms.EmailField()
            else:
                self.fields['email'] = forms.EmailField(required=False)

    def _validate_unique(self, url=None, guid=None):
        identifiers = Q()
        if url is not None:
            identifiers |= (Q(external_url=url) | Q(files__url=url) |
                            Q(original_url=url))
        if guid is not None:
            identifiers |= Q(guid=guid)
        videos = Video.objects.filter(identifiers,
                                      ~Q(status=Video.HIDDEN),
                                      site=Site.objects.get_current())

        # HACK: We set attributes on the form so that we can provide
        # backwards-compatible template context. We should remove this when it's
        # no longer needed.
        try:
            video = videos[0]
        except IndexError:
            self.duplicate_video = None
        else:
            self.duplicate_video = video
            raise ValidationError("That video has already been submitted!")

    def clean(self):
        cleaned_data = self.cleaned_data
        url = cleaned_data['url']
        if not cleaned_data['submit_duplicate']:
            self._validate_unique(url=url)

        self.video = None
        try:
            self.video = vidscraper.auto_scrape(url, api_keys=API_KEYS)
        except (UnhandledVideo, urllib2.URLError):
            pass
        else:
            if not cleaned_data['submit_duplicate']:
                if self.video.link is not None and url != self.video.link:
                    self._validate_unique(url=url, guid=self.video.guid)
                elif self.video.guid is not None:
                    self._validate_unique(guid=self.video.guid)
        return cleaned_data

    def save(self):
        if self.video is not None:
            video = Video.from_vidscraper_video(self.video, commit=False)
        else:
            video = Video()
        video.original_url = self.cleaned_data['url']
        if self.request.user.is_authenticated():
            video.owner = self.request.user
        else:
            video.owner_session = self.request.session
            video.owner_email = self.cleaned_data['email']

        if hasattr(video, 'save_m2m'):
            video.save(update_index=False)
            video.save_m2m()
        else:
            video.save()
        return video
    save.alters_data = True

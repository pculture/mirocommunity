import urllib2

from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db.models import Q
import floppyforms as forms
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
            # Force creation of a session key.
            if not self.request.session.session_key:
                self.request.session.create()
            self.session_key = self.request.session.session_key
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
                                      site=Site.objects.get_current())
        # For personal videos, anything is a duplicate if it hasn't already
        # been hidden. For other people's videos, it's only a duplicate if
        # their video is already published.
        own_videos = videos.exclude(status=Video.HIDDEN)
        other_videos = videos.filter(status=Video.PUBLISHED)
        if self.request.user.is_authenticated():
            own_videos = own_videos.filter(owner=self.request.user)
            other_videos = other_videos.exclude(owner=self.request.user)
        else:
            own_videos = own_videos.filter(owner_session_id=self.session_key)
            other_videos = other_videos.exclude(owner_session_id=self.session_key)

        # HACK: We set attributes on the form so that we can provide
        # backwards-compatible template context. We should remove this when it's
        # no longer needed.
        try:
            self.own_duplicate = own_videos[0]
        except IndexError:
            pass
        try:
            self.other_duplicate = other_videos[0]
        except IndexError:
            pass

        if self.own_duplicate or self.other_duplicate:
            raise ValidationError("That video has already been submitted!")

    def clean(self):
        cleaned_data = self.cleaned_data
        url = cleaned_data.get('url')

        self.vidscraper_video = None
        self.own_duplicate = None
        self.other_duplicate = None

        if not url:
            return cleaned_data

        if not cleaned_data['submit_duplicate']:
            self._validate_unique(url=url)

        try:
            self.vidscraper_video = vidscraper.auto_scrape(url, api_keys=API_KEYS)
        except (UnhandledVideo, urllib2.URLError):
            pass
        else:
            if not cleaned_data['submit_duplicate']:
                if (self.vidscraper_video.link is not None and
                        url != self.vidscraper_video.link):
                    self._validate_unique(url=url,
                                          guid=self.vidscraper_video.guid)
                elif self.vidscraper_video.guid is not None:
                    self._validate_unique(guid=self.vidscraper_video.guid)
        return cleaned_data

    def save(self):
        if self.vidscraper_video is not None:
            video = Video.from_vidscraper_video(self.vidscraper_video,
                                                commit=False)
        else:
            video = Video()
        video.original_url = self.cleaned_data['url']
        if self.request.user.is_authenticated():
            video.owner = self.request.user
        else:
            video.owner_session_id = self.request.session.session_key
            video.owner_email = self.cleaned_data['email']

        if hasattr(video, 'save_m2m'):
            video.save(update_index=False)
            video.save_m2m()
        else:
            video.save()
        return video
    save.alters_data = True

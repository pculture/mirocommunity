from django import forms
from django.conf import settings
from django.contrib.sites.models import Site

from localtv.contrib.contests.models import Contest, ContestVideo
from localtv.models import Video


class ContestAdminForm(forms.ModelForm):
    detail_columns = forms.MultipleChoiceField(
                                        choices=Contest.DETAIL_COLUMN_CHOICES,
                                        widget=forms.CheckboxSelectMultiple)
    videos = forms.ModelMultipleChoiceField(required=False,
                            queryset=Video.objects.filter(status=Video.ACTIVE,
                                                          site=settings.SITE_ID))

    class Meta:
        model = Contest
        # Using fields until https://code.djangoproject.com/ticket/12337
        # is resolved.
        #exclude = ('videos', 'site', 'detail_columns')
        fields = ('name', 'description', 'votes_per_user', 'allow_downvotes',
                  'submissions_open', 'voting_open', 'display_vote_counts',
                  'rules')

    def __init__(self, *args, **kwargs):
        super(ContestAdminForm, self).__init__(*args, **kwargs)
        self.initial['detail_columns'] = self.instance.detail_columns.split(
                                                                          ',')
        if self.instance.pk:
            self.initial['videos'] = self.instance.videos.all()

    def clean_detail_columns(self):
        return ','.join(self.cleaned_data['detail_columns'])

    def _post_clean(self):
        super(ContestAdminForm, self)._post_clean()

        if self.instance.site_id is None:
            self.instance.site = Site.objects.get_current()

        if 'detail_columns' in self.cleaned_data:
            self.instance.detail_columns = self.cleaned_data['detail_columns']

    def save(self, commit=True):
        instance = super(ContestAdminForm, self).save(commit)
        def save_m2m():
            current_pks = set(instance.videos.values_list('pk', flat=True))
            new_pks = set((v.pk for v in self.cleaned_data['videos']))
            remove_pks = current_pks - new_pks
            add_pks = new_pks - current_pks

            ContestVideo.objects.filter(contest=instance,
                                        video__in=remove_pks).delete()
            ContestVideo.objects.bulk_create([
                ContestVideo(video_id=pk, contest=instance)
                for pk in add_pks])

        if commit:
            save_m2m()
        else:
            self.save_m2m = save_m2m
        return instance

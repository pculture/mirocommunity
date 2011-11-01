# Copyright 2011 - Participatory Culture Foundation
# 
# This file is part of Miro Community.
# 
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
# 
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from voting.models import Vote

from localtv.models import Category, Video, CategoryVideo
from localtv.contrib.contest.models import ContestSettings


class VotingForm(forms.Form):
    VOTE_CHOICES = (
        ('up', _('Up')),
        ('clear', _('Clear'))
    )

    vote = forms.ChoiceField(choices=VOTE_CHOICES)
    category = forms.ModelChoiceField(
                   queryset=Category.objects.all(),
                   to_field_name='slug'
               )
    videos = forms.ModelChoiceField(queryset=Video.objects.all())

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(VotingForm, self).__init__(*args, **kwargs)
        current_site = Site.objects.get_current()
        category_qs = Category.objects.filter(
                          site=current_site,
                          contestsettings__site=current_site,
                      )
        # force qs evaluation.
        len(category_qs)

        self.fields['category'].queryset = category_qs
        self.fields['videos'].queryset = Video.objects.filter(
                                                    categories__in=category_qs)

    def clean_vote(self):
        vote = self.cleaned_data['vote']
        if vote == 'up':
            return 1
        return 0

    def clean(self):
        cleaned_data = self.cleaned_data
        try:
            self.category_video = CategoryVideo.objects.get(
                category = cleaned_data['category'],
                video = cleaned_data['video']
            )
        except CategoryVideo.DoesNotExist:
            raise ValidationError("The selected video is not in the selected category.")
        
        if cleaned_data['vote'] != 'clear':
            categoryvideo_pks = CategoryVideo.objects.filter(
                category=cleaned_data['category'],
            ).values_list('pk', flat=True)
            user_votes_for_category = Vote.objects.filter(
                content_type=ContentType.objects.get_for_model(CategoryVideo),
                object_id__in=categoryvideo_pks,
                user=self.user
            ).count()
            contest_settings = ContestSettings.objects.get_current()
            if user_votes_for_category >= contest_settings.max_votes:
                raise ValidationError(_(u"Only %d votes can be made per category"
                                        % contest_settings.max_votes))

    def save(self):
        vote = self.cleaned_data['vote']
        Vote.objects.record_vote(self.category_video, self.user, vote)


class AdminForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(
                     queryset=Category.objects.all(),
                     widget=forms.CheckboxSelectMultiple
                 )

    def __init__(self, *args, **kwargs):
        super(AdminForm, self).__init__(*args, **kwargs)
        self.fields['categories'].queryset = Category.objects.filter(
                                           site=Site.objects.get_current(),
                                       )

    class Meta:
        model = ContestSettings
        exclude = ('site',)
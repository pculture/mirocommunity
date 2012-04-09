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

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _

from localtv.models import Category, Video


class Contest(models.Model):
    #: The name of this contest.
    name = models.CharField(max_length=100)

    #: The site this contest is tied to.
    site = models.ForeignKey(Site)

    #: Categories for which this contest is open. If no categories are
    #: selected, the contest will be open for all categories.
    categories = models.ManyToManyField(Category, blank=True, null=True)

    #: Max number of votes per user for this contest.
    max_votes = models.PositiveIntegerField(validators=[MinValueValidator(1)],
                                            blank=True, null=True, default=1)

    #: Whether down-voting is a valid option.
    allow_downvotes = models.BooleanField(default=True)


class ContestVote(models.Model):
    UP = +1
    DOWN = -1

    VOTE_CHOICES = (
        (UP, u'+'),
        (DOWN, u'-'),
    )

    vote = models.SmallIntegerField(choices=VOTE_CHOICES)
    contest = models.ForeignKey(Contest, related_name='votes')
    video = models.ForeignKey(Video)
    user = models.ForeignKey(User)

    class Meta:
        unique_together = ('contest', 'video', 'user')

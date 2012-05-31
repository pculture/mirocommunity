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

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.sql.aggregates import Aggregate
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _

from localtv.models import Video


class Contest(models.Model):
    NEW = '1'
    RANDOM = '2'
    TOP = '3'
    DETAIL_COLUMN_CHOICES = (
        (NEW, _("Show new submissions")),
        (RANDOM, _("Show all submissions (randomized)")),
        (TOP, _("Show top voted videos"))
    )
    #: The name of this contest.
    name = models.CharField(max_length=100)

    #: A description of the contest.
    description = models.TextField(blank=True)

    #: Columns to display on the contest detail page.
    detail_columns = models.CommaSeparatedIntegerField(max_length=10,
                                                choices=DETAIL_COLUMN_CHOICES,
                                                blank=True)

    #: The site this contest is tied to.
    site = models.ForeignKey(Site)

    #: Max number of votes per user for this contest.
    votes_per_user = models.PositiveIntegerField(blank=True, null=True,
                                            validators=[MinValueValidator(1)],
                                            default=1, help_text=_("Leave "
                                            "blank for unlimited votes. Even "
                                            "with unlimited votes, each user "
                                            "can only vote once per video."))

    #: Videos which have been submitted to this contest.
    videos = models.ManyToManyField(Video, blank=True, through='ContestVideo')

    #: Whether down-voting is a valid option.
    allow_downvotes = models.BooleanField(default=True)

    #: Whether videos can be submitted to the contest.
    submissions_open = models.BooleanField(default=False)

    #: Whether videos can be voted on.
    voting_open = models.BooleanField(default=False)

    #: Whether the actual vote counts should be displayed by the videos.
    display_vote_counts = models.BooleanField(default=False)

    @property
    def slug(self):
        return slugify(self.name)

    def __unicode__(self):
        return unicode(self.name)

    def get_absolute_url(self):
        return reverse('contests_contest_detail',
                       kwargs={'pk': self.pk,
                               'slug': self.slug})

    def get_listing_url(self):
        return reverse('contests_contest_listing',
                       kwargs={'pk': self.pk,
                               'slug': self.slug})


class ContestVideo(models.Model):
    contest = models.ForeignKey(Contest)
    video = models.ForeignKey(Video)
    added = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('contest', 'video')


class ContestVote(models.Model):
    UP = +1
    DOWN = -1

    VOTE_CHOICES = (
        (UP, u'+'),
        (DOWN, u'-'),
    )

    vote = models.SmallIntegerField(choices=VOTE_CHOICES)
    user = models.ForeignKey(User)
    contestvideo = models.ForeignKey(ContestVideo)

    class Meta:
        unique_together = ('contestvideo', 'user')


class UpVotesAggregate(models.Aggregate):
    def __init__(self):
        models.Aggregate.__init__(self, "contestvideo")

    def add_to_query(self, query, alias, col, source, is_summary):
        aggregate = UpVotesAggregateSQL(col, source=source,
                                        is_summary=is_summary,
                                        **self.extra)
        query.aggregates[alias] = aggregate


class UpVotesAggregateSQL(Aggregate):
    is_ordinal = True
    sql_template = ('(SELECT COUNT(*) FROM %s INNER JOIN %s ON (%s.%s == %s.%s) WHERE %s.%s = %s.%s AND %s.%s == %s)')

    def as_sql(self, qn, connection):
        contests_vote = qn("contests_contestvote")
        contests_video = qn("contests_contestvideo")
        localtv_video = qn("localtv_video")
        id_ = qn("id")
        video_id = qn("video_id")
        contestvideo_id = qn("contestvideo_id")
        vote = qn("vote")
        return self.sql_template % (
            # FROM
            contests_vote,
            # INNER JOIN
            contests_video,
            # ON
            contests_vote, contestvideo_id,
            # ==
            contests_video, id_,
            # WHERE
            contests_video, video_id,
            # ==
            localtv_video, id_,
            # AND
            contests_vote, vote,
            # ==
            1)


class AllVotesAggregate(models.Aggregate):
    def __init__(self):
        models.Aggregate.__init__(self, "contestvideo")

    def add_to_query(self, query, alias, col, source, is_summary):
        aggregate = AllVotesAggregateSQL(col, source=source,
                                        is_summary=is_summary,
                                        **self.extra)
        query.aggregates[alias] = aggregate


class AllVotesAggregateSQL(Aggregate):
    is_ordinal = True
    sql_template = ('(SELECT SUM(%s) FROM %s INNER JOIN %s ON (%s.%s = %s.%s) WHERE %s.%s = %s.%s)')

    def as_sql(self, qn, connection):
        contests_vote = qn("contests_contestvote")
        contests_video = qn("contests_contestvideo")
        localtv_video = qn("localtv_video")
        id_ = qn("id")
        video_id = qn("video_id")
        contestvideo_id = qn("contestvideo_id")
        vote = qn("vote")
        return self.sql_template % (
            # SUM
            vote,
            # FROM
            contests_vote,
            # INNER JOIN
            contests_video,
            # ON
            contests_vote, contestvideo_id,
            # ==
            contests_video, id_,
            # WHERE
            contests_video, video_id,
            # ==
            localtv_video, id_)

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
from django.contrib.sites.models import Site
from django.core.validators import MinValueValidator
from django.db import models

from localtv.models import Category


class ContestSettingsManager(models.Manager):
    # This is a template for future settings managers.
    def get_current(self, **kwargs):
        current_site = Site.objects.get_current()
        try:
            current_site.contestsettings
        except ContestSettings.DoesNotExist:
            current_site.contestsettings = self.get_or_create(
                                                site=current_site)[0]
        return current_site.contestsettings



class ContestSettings(models.Model):
    objects = ContestSettingsManager()

    #: The site these settings are for.
    site = models.OneToOneField(Site)

    #: Categories for which voting is enabled.
    categories = models.ManyToManyField(Category, blank=True, null=True)

    #: Max number of votes per category
    max_votes = models.PositiveIntegerField(validators=[MinValueValidator(1)],
                                            blank=True, null=True)

    def get_absolute_url(self):
        return reverse('localtv_contest_admin')
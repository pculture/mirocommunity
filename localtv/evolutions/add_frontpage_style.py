from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('SiteLocation', 'frontpage_style', models.CharField, initial=u'list', max_length=32)
]

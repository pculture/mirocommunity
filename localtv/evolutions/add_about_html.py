from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('SiteLocation', 'about_html', models.TextField, initial='')
]

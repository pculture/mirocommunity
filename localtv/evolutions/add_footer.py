from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('SiteLocation', 'footer_html', models.TextField, initial='')
]

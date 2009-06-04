from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('SiteLocation', 'background', models.ImageField, initial='', max_length=100),
    AddField('SiteLocation', 'logo', models.ImageField, initial='', max_length=100),
    AddField('SiteLocation', 'css', models.TextField, initial=''),
    DeleteModel('SiteCss')
]

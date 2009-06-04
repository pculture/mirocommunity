from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('SiteLocation', 'submission_requires_login', models.BooleanField, initial=False),
    AddField('SiteLocation', 'display_submit_button', models.BooleanField, initial=True)
]

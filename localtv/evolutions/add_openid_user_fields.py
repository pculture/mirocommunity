from django_evolution.mutations import *
from django.db import models

# slight misnomer, also adds the search field to Video

class NULL:
    """
    A hack to get django-evolution to set the id fields to NULL in the
    database.
    """
    @staticmethod
    def __repr__():
        return 'NULL'

MUTATIONS = [
    AddField('Feed', 'openid_user', models.ForeignKey, initial=NULL, null=True, related_model='localtv.OpenIdUser'),
    AddField('SavedSearch', 'openid_user', models.ForeignKey, initial=NULL, null=True, related_model='localtv.OpenIdUser'),
    AddField('Video', 'search', models.ForeignKey, initial=NULL, null=True, related_model='localtv.SavedSearch'),
    AddField('Video', 'openid_user', models.ForeignKey, initial=NULL, null=True, related_model='localtv.OpenIdUser')
]

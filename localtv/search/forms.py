from haystack import forms
from localtv import models
from localtv import search

class VideoSearchForm(forms.SearchForm):

    def search(self):
        self.clean()
        sqs = self.searchqueryset.models(models.Video)
        sqs = search.auto_query(self.cleaned_data['q'], sqs)

        return sqs

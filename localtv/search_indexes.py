from haystack import indexes
from haystack import site
from localtv.models import Video, VIDEO_STATUS_ACTIVE


class VideoIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    feed = indexes.IntegerField(model_attr='feed__pk', null=True)
    search = indexes.IntegerField(model_attr='search__pk', null=True)
    user = indexes.IntegerField(model_attr='user__pk', null=True)
    tags = indexes.MultiValueField()
    categories = indexes.MultiValueField()
    authors = indexes.MultiValueField()
    playlists = indexes.MultiValueField()

    def get_queryset(self):
        """
        Custom queryset to only search approved videos.
        """
        return Video.objects.filter(status=VIDEO_STATUS_ACTIVE)

    def get_updated_field(self):
        return 'when_modified'

    def _prepare_field(self, video, field, attr='pk', normalize=int):
        return [normalize(getattr(rel, attr))
                for rel in getattr(video, field).all()]

    def prepare_tags(self, video):
        return self._prepare_field(video, 'tags', 'name', unicode)

    def prepare_categories(self, video):
        return self._prepare_field(video, 'categories')

    def prepare_authors(self, video):
        return self._prepare_field(video, 'authors')

    def prepare_playlists(self, video):
        return self._prepare_field(video, 'playlists')

site.register(Video, VideoIndex)

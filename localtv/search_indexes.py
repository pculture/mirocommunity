from haystack import indexes
from haystack import site
from localtv.models import Video, VIDEO_STATUS_ACTIVE


class VideoIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    best_date = indexes.DateTimeField(model_attr='best_date')

    def get_queryset(self):
        """
        Custom queryset to only search approved videos.
        """
        return Video.objects.new(status=VIDEO_STATUS_ACTIVE)

site.register(Video, VideoIndex)

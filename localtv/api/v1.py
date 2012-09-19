from django.conf import settings
from django.contrib.auth.models import User
from tastypie import fields
from tastypie.api import Api
from tastypie.resources import ModelResource

from localtv.models import Video, Feed, SavedSearch, Category


class ThumbnailableResource(ModelResource):
    """Handles the crazy thumbnail storage on Thumbnailable subclasses."""
    thumbnail = fields.CharField(null=True, readonly=True)

    def dehydrate_thumbnail(self, bundle):
        if not bundle.obj.thumbnail:
            thumbnail = None
        else:
            thumbnail = bundle.obj.thumbnail.url
        return thumbnail


class UserResource(ModelResource):
    class Meta:
        queryset = User.objects.all()
        fields = ('id', 'username', 'first_name', 'last_name')


class CategoryResource(ModelResource):
    class Meta:
        queryset = Category.objects.filter(site=settings.SITE_ID)
        fields = ('id', 'name', 'slug', 'logo', 'description',)


class FeedResource(ThumbnailableResource):
    class Meta:
        queryset = Feed.objects.filter(status=Feed.ACTIVE,
                                       site=settings.SITE_ID)
        fields = ('id', 'auto_approve', 'auto_update', 'feed_url',
                  'name', 'webpage', 'description', 'last_updated',
                  'when_submitted', 'etag', 'thumbnail')


class SearchResource(ThumbnailableResource):
    class Meta:
        queryset = SavedSearch.objects.filter(site=settings.SITE_ID)
        fields = ('id', 'auto_approve', 'auto_update', 'query_string',
                  'when_created', 'thumbnail')


class VideoResource(ThumbnailableResource):
    when_featured = fields.DateTimeField(attribute='last_featured', null=True)
    categories = fields.ToManyField(CategoryResource, 'categories')
    authors = fields.ToManyField(UserResource, 'authors')
    feed = fields.ToOneField(FeedResource, 'feed', null=True)
    search = fields.ToOneField(SearchResource, 'search', null=True)
    user = fields.ToOneField(UserResource, 'user', null=True)
    tags = fields.ListField(attribute='tags')

    class Meta:
        queryset = Video.objects.filter(status=Video.ACTIVE,
                                        site=settings.SITE_ID)
        fields = ('id', 'file_url', 'when_modified', 'when_submitted',
                  'when_published', 'website_url', 'embed_code',
                  'guid', 'tags', 'thumbnail')


api = Api(api_name='v1')
api.register(VideoResource())
api.register(FeedResource())
api.register(SearchResource())
api.register(CategoryResource())
api.register(UserResource())

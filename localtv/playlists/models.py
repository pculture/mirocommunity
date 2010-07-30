from django.db import models

from localtv.models import Video

class Playlist(models.Model):
    name = models.CharField(
        max_length=80, verbose_name='Name')
    slug = models.SlugField(
        verbose_name='Slug',
        help_text=('The "slug" is the URL-friendly version '
                   "of the name.  It is usually lower-case "
                   "and contains only letters, numbers and "
                   "hyphens."))
    description = models.TextField(
        blank=True, verbose_name='Description (HTML)',
        help_text=("The description is not prominent "
                   "by default, but some themes may "
                   "show it."))
    user = models.ForeignKey('auth.User')

    items = models.ManyToManyField(Video,
                                   through='PlaylistItem',
                                   related_name='playlists')

    class Meta:
        ordering = ['name']
        unique_together = [('user', 'slug'),
                           ('user', 'name')]

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('localtv_playlist_view', (self.pk, self.slug))

    def _item_for(self, video):
        return PlaylistItem.objects.get(playlist=self, video=video)

    def add_video(self, video):
        PlaylistItem.objects.create(
            playlist=self,
            video=video)

    def order_videos(self, video_set):
        self.set_playlistitem_order(
            [PlaylistItem.objects.filter(playlist=self,
                                      video=video).values_list('pk',
                                                               flat=True).get()
             for video in video_set])

    @property
    def video_set(self):
        return self.items.order_by('playlistitem___order')

    def next_video(self, video):
        try:
            return self._item_for(video).get_next_in_order().video
        except PlaylistItem.DoesNotExist:
            return None

    def previous_video(self, video):
        try:
            return self._item_for(video).get_previous_in_order().video
        except PlaylistItem.DoesNotExist:
            return None


class PlaylistItem(models.Model):
    playlist = models.ForeignKey(Playlist)
    video = models.ForeignKey(Video)

    class Meta:
        order_with_respect_to = 'playlist'
        unique_together = ('playlist', 'video')


    def __unicode__(self):
        return u'#%i: %s (%s)' % (self._order, self.video, self.playlist)

    @property
    def index(self):
        # can't access _variables from templates
        return self._order + 1

    def get_two_from_order(self):
        if self.playlist.items.count() <= 2:
            return self.playlist.items.all()
        if self._order == 0: # first video:
            next = self.get_next_in_order()
            try:
                # next two videos
                return (next, next.get_next_in_order())
            except PlaylistItem.DoesNotExist:
                # only one next video
                return (next,)
        previous = self.get_previous_in_order()
        try:
            # previous and next videos
            return (previous, self.get_next_in_order())
        except PlaylistItem.DoesNotExist:
            pass

        # last video, return the previous video and ourself
        return (previous, self)

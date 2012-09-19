from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    'localtv.playlists.views',
    (r'^$', 'index', {}, 'localtv_playlist_index'),
    (r'^(\d+)$', 'view', {}, 'localtv_playlist_view'),
    (r'^(\d+)/([\w-]+)/?$', 'view', {}, 'localtv_playlist_view'),
    (r'^edit/(\d+)$', 'edit', {}, 'localtv_playlist_edit'),
    (r'^add/(\d+)$', 'add_video', {}, 'localtv_playlist_add_video'),
    (r'^public/(\d+)$', 'public', {}, 'localtv_playlist_public'),
    (r'^private/(\d+)$', 'private', {}, 'localtv_playlist_private'),
)

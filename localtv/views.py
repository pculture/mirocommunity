from django.contrib import comments
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import resolve, Resolver404
from django.conf import settings
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.encoding import iri_to_uri
from django.views.generic import TemplateView, DetailView

from localtv.models import Video, Watch, Category, SiteSettings
from localtv.search.forms import SearchForm
from localtv.search.utils import NormalizedVideoList

from localtv.playlists.models import Playlist, PlaylistItem


MAX_VOTES_PER_CATEGORY = getattr(settings, 'MAX_VOTES_PER_CATEGORY', 3)


class IndexView(TemplateView):
    template_name = 'localtv/index.html'

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        featured_form = SearchForm({'sort': 'featured'})
        popular_form = SearchForm({'sort': 'popular'})
        new_form = SearchForm({'sort': 'newest'})

        video_pks = Video.objects.filter(site=settings.SITE_ID,
                                         status=Video.ACTIVE
                                         ).values_list('pk', flat=True)
        recent_comments = comments.get_model().objects.filter(
            site=settings.SITE_ID,
            content_type=ContentType.objects.get_for_model(Video),
            object_pk__in=video_pks,
            is_removed=False,
            is_public=True).order_by('-submit_date')

        context.update({
            'featured_videos': NormalizedVideoList(featured_form.search()),
            'popular_videos': NormalizedVideoList(popular_form.search()),
            'new_videos': NormalizedVideoList(new_form.search()),
            'comments': recent_comments
        })
        return context


def about(request):
    return render_to_response(
        'localtv/about.html',
        {}, context_instance=RequestContext(request))


class VideoView(DetailView):
    pk_url_kwarg = 'video_id'
    context_object_name = 'current_video'
    template_name = 'localtv/view_video.html'
    model = Video

    # Modules to display in the right sidebar on the video page.
    sidebar_modules = ['localtv/_modules/suggested_videos.html']

    def get_queryset(self):
        qs = super(VideoView, self).get_queryset()
        if not self.request.user_is_admin():
            qs = qs.filter(status=Video.ACTIVE)
        return qs.filter(site=settings.SITE_ID)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        abs_url = self.object.get_absolute_url()
        if self.kwargs['slug'] is None or iri_to_uri(request.path) != abs_url:
            return HttpResponseRedirect(abs_url)

        context = self.get_context_data(object=self.object)

        Watch.add(request, self.object)
        return self.render_to_response(context)

    def get_sidebar_modules(self):
        return self.sidebar_modules

    def get_context_data(self, **kwargs):
        context = super(VideoView, self).get_context_data(**kwargs)
        context.update({
            'sidebar_modules': self.get_sidebar_modules(),
            # set edit_video_form to True if the user is an admin for
            # backwards-compatibility
            'edit_video_form': self.request.user_is_admin(),
        })

        site_settings = SiteSettings.objects.get_current()
        # Data for generating popular videos list.
        popular_form_data = {'sort': 'popular'}

        try:
            category_obj = self.object.categories.all()[0]
        except IndexError:
            pass
        else:
            # If there are categories, prefer the category that the user
            # just came from the list view of.
            referrer = self.request.META.get('HTTP_REFERER')
            host = self.request.META.get('HTTP_HOST')
            if referrer and host:
                if referrer.startswith('http://') or \
                        referrer.startswith('https://'):
                    referrer = referrer[referrer.index('://')+3:]
                if referrer.startswith(host):
                    referrer = referrer[len(host):]
                    try:
                        view, args, kwargs = resolve(referrer)
                    except Resolver404:
                        pass
                    else:
                        from localtv.urls import category_videos
                        if view == category_videos:
                            try:
                                category_obj = self.object.categories.get(
                                    slug=kwargs['slug'],
                                    site=site_settings.site)
                            except Category.DoesNotExist:
                                pass

            context['category'] = category_obj
            popular_form_data['category'] = [category_obj]

        form = SearchForm(popular_form_data)
        popular_videos = form.search()
        context['popular_videos'] = NormalizedVideoList(popular_videos)

        if site_settings.playlists_enabled:
            # showing playlists
            if self.request.user.is_authenticated():
                if self.request.user_is_admin() or \
                        site_settings.playlists_enabled == 1:
                    # user can add videos to playlists
                    context['playlists'] = Playlist.objects.filter(
                        user=self.request.user)

            playlistitem_qs = self.object.playlistitem_set.all()
            if self.request.user_is_admin():
                # show all playlists
                pass
            elif self.request.user.is_authenticated():
                # public playlists or my playlists
                playlistitem_qs = playlistitem_qs.filter(
                                        Q(playlist__status=Playlist.PUBLIC) |
                                        Q(playlist__user=self.request.user))
            else:
                # just public playlists
                playlistitem_qs = playlistitem_qs.filter(
                                            playlist__status=Playlist.PUBLIC)
            context['playlistitem_set'] = playlistitem_qs
            if 'playlist' in self.request.GET:
                try:
                    playlist = Playlist.objects.get(
                                              pk=self.request.GET['playlist'])
                except (Playlist.DoesNotExist, ValueError):
                    pass
                else:
                    if (playlist.is_public() or
                            self.request.user_is_admin() or
                            (self.request.user.is_authenticated() and
                            playlist.user_id == self.request.user.pk)):
                        try:
                            context['playlistitem'] = (
                                self.object.playlistitem_set.get(
                                                           playlist=playlist))
                        except PlaylistItem.DoesNotExist:
                            pass

        return context


def share_email(request, content_type_pk, object_id):
    from email_share import views, forms
    site_settings = SiteSettings.objects.get_current()
    return views.share_email(request, content_type_pk, object_id,
                             {'site': site_settings.site,
                              'site_settings': site_settings},
                             form_class = forms.ShareMultipleEmailForm
                             )

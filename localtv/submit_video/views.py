from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.forms.models import modelform_factory
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_protect
from django.views.generic import FormView, CreateView
from django.utils.decorators import method_decorator
from tagging.utils import parse_tag_input

from localtv.decorators import request_passes_test
from localtv.models import SiteSettings, Video
from localtv.signals import submit_finished
from localtv.submit_video import forms
from localtv.submit_video.utils import is_video_url
from localtv.utils import get_or_create_tags


def _has_submit_permissions(request, *args, **kwargs):
    site_settings = SiteSettings.objects.get_current()
    if not site_settings.submission_requires_login:
        return True
    else:
        if site_settings.display_submit_button:
            return request.user.is_authenticated() and request.user.is_active
        else:
            return request.user_is_admin()


can_submit_video = request_passes_test(_has_submit_permissions)


class SubmitURLView(FormView):
    form_class = forms.SubmitURLForm
    session_key = "localtv_submit_video_info"
    template_name = "localtv/submit_video/submit.html"

    #: The url which this view will redirect to if the url can be scraped.
    scraped_url = None

    #: The url which this view will redirect to if the url is a video file.
    direct_url = None

    #: The url which this view will redirect to if the url isn't recognized.
    embed_url = None

    def get(self, request, *args, **kwargs):
        return FormView.post(self, request, *args, **kwargs)

    @method_decorator(csrf_protect)
    def post(self, request, *args, **kwargs):
        # This method should be disallowed. Some forms may still use it in old
        # templates, so we handle it for backwards-compatibility.
        return self.get(request, *args, **kwargs)

    def get_session_key(self):
        return self.session_key

    def get_form(self, form_class):
        kwargs = self.get_form_kwargs()
        # If it looks like the form has been submitted via GET, set the data
        # kwarg to the GET data.
        if set(self.request.GET) & set(form_class.base_fields):
            kwargs['data'] = self.request.GET
        return form_class(**kwargs)

    def form_valid(self, form):
        video = form.video_cache
        url = form.cleaned_data['url']
        # This bit essentially just preserves the old behavior; really, the
        # views that are redirected to are all instances of SubmitVideoView.

        video_file = None if video is None else video.get_file()
        if video is not None and (video.embed_code or
                (video_file and not video_file.expires)):
            success_url = self.scraped_url
        elif is_video_url(url):
            success_url = self.direct_url
        else:
            success_url = self.embed_url

        self.success_url = "%s?%s" % (success_url, self.request.GET.urlencode())

        key = self.get_session_key()
        self.request.session[key] = {
            'video': video,
            'url': url
        }
        return super(SubmitURLView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(SubmitURLView, self).get_context_data(**kwargs)
        # HACK to provide backwards-compatible context.
        form = context['form']
        context['was_duplicate'] = getattr(form, 'was_duplicate', False)
        context['video'] = getattr(form, 'duplicate_video', None)

        # Provide the video pk explicitly since the backwards-compatible context
        # doesn't allow access to the video's pk if the video's status is not
        # ACTIVE.
        context['video_pk'] = getattr(form, 'duplicate_video_pk', None)
        return context


class SubmitVideoView(CreateView):
    session_key = "localtv_submit_video_info"
    #: The url name for the success url.
    thanks_url_name = None
    #: The url for the base submit view. Requests that don't have the proper
    #: session information will be redirected there.
    submit_video_url = None

    #: A list or tuple of fields to include in the form.
    form_fields = None

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        session_key = self.get_session_key()
        if (session_key not in request.session or
            not request.session[session_key].get('url', None)):
            return HttpResponseRedirect(self.submit_video_url)
        return super(SubmitVideoView, self).dispatch(request, *args, **kwargs)

    def get_session_key(self):
        return self.session_key

    def get_success_url(self):
        return reverse(self.thanks_url_name, args=[self.object.pk])

    def get_form_class(self):
        fields = self.form_fields
        session_key = self.get_session_key()
        try:
            session_dict = self.request.session[session_key]
            self.video = session_dict['video']
            self.url = session_dict['url']
        except KeyError:
            raise Http404

        self.object = self.get_object()

        return modelform_factory(Video, form=self.form_class, fields=fields)

    def get_initial(self):
        initial = super(SubmitVideoView, self).get_initial()
        if getattr(self.video, 'tags', None):
            initial.update({
                'tags': get_or_create_tags(self.video.tags),
            })
        return initial

    def get_object(self):
        if self.video is not None:
            return Video.from_vidscraper_video(self.video, commit=False)
        return Video()

    def get_form_kwargs(self):
        kwargs = super(SubmitVideoView, self).get_form_kwargs()
        kwargs.update({
            'request': self.request,
            'url': self.url
        })
        return kwargs

    def get_template_names(self):
        return [self.template_name]

    def form_valid(self, form):
        response = super(SubmitVideoView, self).form_valid(form)
        identifiers = Q()
        if self.object.website_url:
            identifiers |= Q(website_url=self.object.website_url)
        if self.object.file_url:
            identifiers |= Q(file_url=self.object.file_url)
        if self.object.guid:
            identifiers |= Q(guid=self.object.guid)
        Video.objects.filter(identifiers, site=Site.objects.get_current(),
                             status=Video.HIDDEN).delete()
        del self.request.session[self.get_session_key()]
        submit_finished.send(sender=self.object)
        return response

    def get_context_data(self, **kwargs):
        context = super(SubmitVideoView, self).get_context_data(**kwargs)
        # Provided for backwards-compatibility.
        context['data'] = {
            'link': self.object.website_url,
            'publish_date': self.object.when_published,
            'tags': parse_tag_input(context['form'].initial.get('tags', '')),
            'title': self.object.name,
            'description': self.object.description,
            'thumbnail_url': self.object.thumbnail_url,
            'user': self.object.video_service_user,
            'user_url': self.object.video_service_url,
        }
        return context


def submit_thanks(request, video_id=None, template_name=None,
                  extra_context=None):
    if template_name is None:
        template_name = 'localtv/submit_video/thanks.html'
    if request.user_is_admin() and video_id:
        context = {
            'video': Video.objects.get(pk=video_id)
            }
    else:
        context = {}
    if extra_context is not None:
        context.update(extra_context)
    return render_to_response(
        template_name, context,
        context_instance=RequestContext(request))

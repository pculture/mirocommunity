from django.core.urlresolvers import reverse
from django.conf import settings
from django.http import Http404

from localtv.decorators import request_passes_test
from localtv.submit_video import views as submit_views

from localtv.contrib.contests.models import Contest, ContestVideo

def _has_contest_submit_permissions(request, pk, *args, **kwargs):
    if not submit_views._has_submit_permissions(request):
        return False
    if request.user_is_admin():
        return True
    try:
        contest = Contest.objects.get(pk=pk)
    except Contest.DoesNotExist:
        raise Http404
    return contest.submissions_open


can_submit_video = request_passes_test(_has_contest_submit_permissions)


class ContestSubmitMixin(object):
    session_key_template = 'localtv_contests_submit_video_info_%s_%s'

    def dispatch(self, *args, **kwargs):
        self.contest = Contest.objects.get(pk=kwargs['pk'])
        return super(ContestSubmitMixin, self).dispatch(*args, **kwargs)

    def get_session_key(self):
        return self.session_key_template % (
            settings.SITE_ID, self.contest.pk)

    def get_context_data(self, **kwargs):
        context = super(ContestSubmitMixin, self).get_context_data(**kwargs)
        context['contest'] = self.contest
        return context

class SubmitURLView(ContestSubmitMixin, submit_views.SubmitURLView):
    template_name = "contests/submit_video/submit.html"

    @property
    def scraped_url(self):
        return reverse('localtv_contests_submit_scraped_video',
                       args=[self.contest.pk, self.contest.slug])

    @property
    def embed_url(self):
        return reverse('localtv_contests_submit_embedrequest_video',
                       args=[self.contest.pk, self.contest.slug])

    @property
    def direct_url(self):
        return reverse('localtv_contests_submit_directlink_video',
                       args=[self.contest.pk, self.contest.slug])


class SubmitVideoView(ContestSubmitMixin, submit_views.SubmitVideoView):

    @property
    def submit_video_url(self):
        return reverse('localtv_contests_submit_video',
                       args=[self.contest.pk, self.contest.slug])

    def get_success_url(self):
        return reverse('localtv_contests_submit_thanks',
                       args=[self.contest.pk, self.contest.slug])

    def form_valid(self, form):
        response = super(SubmitVideoView, self).form_valid(form)
        ContestVideo.objects.create(
            video=self.object,
            contest=self.contest)
        return response


def submit_thanks(request, pk, slug=None, video_id=None):
    contest = Contest.objects.get(pk=pk)
    return submit_views.submit_thanks(
        request, video_id=video_id,
        template_name='contests/submit_video/thanks.html',
        extra_context={
            'contest': contest
            })

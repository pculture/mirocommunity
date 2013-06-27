from django.views.generic import ListView

from localtv.models import Video


class ModerationView(ListView):
    template_name = 'mirocommunity/admin/moderate.html'
    context_object_name = 'videos'
    model = Video

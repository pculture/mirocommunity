from djam.views.generic import UpdateView, FormView
from django.http import Http404


class ProfileView(UpdateView):
    def get_success_url(self):
        return self.request.path

    def get_object(self):
        if not self.request.user.is_authenticated():
            raise Http404
        return self.request.user


class NotificationsView(FormView):
    def get_success_url(self):
        return self.request.path

    def get_form_kwargs(self):
        if not self.request.user.is_authenticated():
            raise Http404
        kwargs = super(NotificationsView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        return super(NotificationsView, self).form_valid(form)

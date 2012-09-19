from django.contrib.comments.views import comments


def post_comment(request, next=None):
    POST = request.POST.copy()
    POST['user'] = request.user
    request.POST = POST
    return comments.post_comment(request, next)

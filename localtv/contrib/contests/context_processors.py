from django.conf import settings

from localtv.contrib.contests.models import Contest


def contests(request):
	return {'contests': Contest.objects.filter(site=settings.SITE_ID)}

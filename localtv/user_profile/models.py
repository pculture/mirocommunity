import urllib

from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import signals
from django.template import Context, loader
from social_auth.backends.facebook import FacebookBackend
from social_auth.backends.twitter import TwitterBackend
from social_auth.signals import socialauth_registered

from localtv.utils import get_profile_model


class BaseProfile(models.Model):
    """
    Some extra data that we store about users.  Gets linked to a User object
    through the Django authentication system.
    """
    user = models.ForeignKey(User)
    logo = models.ImageField(upload_to="localtv/profile_logos", blank=True,
                             verbose_name='Image')
    location = models.CharField(max_length=200, blank=True, default='')
    description = models.TextField(blank=True, default='')
    website = models.URLField(blank=True, default='')

    class Meta:
        abstract = True

    def __unicode__(self):
        return u"%s for %s" % (self.__class__.__name__, unicode(self.user))


class Profile(BaseProfile):
    class Meta:
        db_table = 'localtv_profile'


def twitter_profile_data(sender, user, response, details, **kwargs):
    profile = get_profile_model()(user=user,
                                  location=response.get('location', ''),
                                  description=response.get('description', ''),
                                  website=response.get('url', ''))
    if response.get('profile_image_url', ''):
        try:
            cf = ContentFile(urllib.urlopen(response['profile_image_url']).read())
        except Exception:
            pass
        else:
            cf.name = response['profile_image_url']
            profile.logo = cf

    profile.save()


socialauth_registered.connect(twitter_profile_data, sender=TwitterBackend)


def facebook_profile_data(sender, user, response, details, **kwargs):
    get_profile_model().objects.create(
        user=user,
        location=response.get('location', ''),
        description=response.get('about_me', ''),
        website=response.get('url', ''))


socialauth_registered.connect(facebook_profile_data, sender=FacebookBackend)


### On creating a new user, if the user has an email address
### XXX If you make changes to the way users are auto-created on video import,
### pay attention to this to make sure that we don't email people who don't care.
def on_user_create_send_welcomed_email(sender, instance=None, raw=None, created=False, **kwargs):
    if not created:
        return # We only care about *new* users.

    # If this is the only user, then skip the email sending.
    if User.objects.all().count() <= 1:
        # We stop right here, and refuse to send email.
        return

    # Note: We're extra careful here: if the user does not have a login-able password,
    # perhaps because the user was created through OpenID or Twitter or Facebook,
    # bail out.
    if not instance.has_usable_password():
        return

    if not instance.email:
        return # We only care about users with email addresses.

    ### Well, in that case, let's send the user a welcome email.
    import localtv.models

    site = localtv.models.SiteSettings.objects.get_current().site

    t = loader.get_template('localtv/user_profile/welcome_message.txt')
    c = Context({'site': site,
                 'user': instance})
    subject = "Welcome to %s" % site.name
    message = t.render(c)

    from django.conf import settings
    EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL,
                 [instance.email]).send(fail_silently=True)


signals.post_save.connect(on_user_create_send_welcomed_email,
                          sender=User)

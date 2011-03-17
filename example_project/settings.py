# Example settings for a Miro Community project

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'localtv.db'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = 'media'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'uploadtemplate.loader.load_template_source',
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'localtv.FixAJAXMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'localtv.SiteLocationMiddleware',
    'openid_consumer.middleware.OpenIDMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    )

ROOT_URLCONF = 'urls'

UPLOADTEMPLATE_MEDIA_ROOT = MEDIA_ROOT + 'uploadtemplate'
UPLOADTEMPLATE_MEDIA_URL = MEDIA_URL + 'uploadtemplate'
UPLOADTEMPLATE_STATIC_ROOTS = [] # other directories which have static files
UPLOADTEMPLATE_TEMPLATE_ROOTS = [] # other directories with templates
UPLOADTEMPLATE_DISABLE_UPLOAD = lambda: not __import__('localtv.models').models.SiteLocation.objects.get_current().get_tier().enforce_permit_custom_template()

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.g
    "../src/miro-community/localtv/templates/",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.comments',
    'django.contrib.flatpages',
    'south',
    'djpagetabs',
    'djvideo',
    'localtv',
    'localtv.admin',
    'localtv.comments',
    'localtv.submit_video',
    'localtv.inline_edit',
    'localtv.user_profile',
    'localtv.playlists',
    'registration',
    'tagging',
    'uploadtemplate',
    'haystack',
    'email_share',
    'celery',
    'notification',
    'socialauth',
    'openid_consumer',
    'paypal',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.media",
    "localtv.context_processor")

LOGIN_REDIRECT_URL = '/'

OPENID_REDIRECT_NEXT = '/accounts/openid/done/'

OPENID_SREG = {"requred": "nickname, email, fullname",
               "policy_url": ""}

#example should be something more like the real thing, i think
OPENID_AX = [{"type_uri": "http://axschema.org/contact/email",
              "count": 1,
              "required": True,
              "alias": "email"},
             {"type_uri": "http://axschema.org/schema/fullname",
              "count":1 ,
              "required": False,
              "alias": "fname"}]

OPENID_AX_PROVIDER_MAP = {'Google': {'email': 'http://axschema.org/contact/email',
                                     'firstname': 'http://axschema.org/namePerson/first',
                                     'lastname': 'http://axschema.org/namePerson/last'},
                          'Default': {'email': 'http://axschema.org/contact/email',
                                      'fullname': 'http://axschema.org/namePerson',
                                      'nickname': 'http://axschema.org/namePerson/friendly'}
                          }


AUTHENTICATION_BACKENDS = (
    'localtv.backend.SiteAdminBackend',
    'socialauth.auth_backends.OpenIdBackend',
    'socialauth.auth_backends.TwitterBackend',
    'socialauth.auth_backends.FacebookBackend',
    )

AUTH_PROFILE_MODULE = 'user_profile.Profile'
COMMENTS_APP = 'localtv.comments'

FLOWPLAYER_SWF_URL = MEDIA_URL + 'swf/flowplayer-3.0.7.swf'
FLOWPLAYER_JS_URL = MEDIA_URL + 'js/flowplayer-3.0.6.min.js'

CACHE_BACKEND = 'locmem://'

# vidscraper keys
from vidscraper.metasearch.sites import vimeo
vimeo.VIMEO_API_KEY = None
vimeo.VIMEO_API_SECRET = None

from vidscraper.sites import ustream
ustream.USTREAM_API_KEY = None

# bit.ly keys
BITLY_LOGIN = None
BITLY_API_KEY = None

# recaptcha keys
RECAPTCHA_PUBLIC_KEY = None
RECAPTCHA_PRIVATE_KEY = None

# django-registration
ACCOUNT_ACTIVATION_DAYS = 7

# django-tagging
FORCE_LOWERCASE_TAGS = True

# celery
BROKER_HOST = 'localhost'
BROKER_PORT = 5672
BROKER_USER = 'celery'
BROKER_PASSWORD = 'testing'
BROKER_VHOST = '/'
CELERY_BACKEND = 'cache' # this MUST be set, otherwise the import page won't be
                         # able to figure out if the task has ended

# haystack search
HAYSTACK_SITECONF = 'example_project.search_sites'
HAYSTACK_SEARCH_ENGINE = 'whoosh'
HAYSTACK_WHOOSH_PATH = 'whoosh_index'

# Facebook options
FACEBOOK_APP_ID = None
FACEBOOK_API_KEY = None
FACEBOOK_SECRET_KEY = None
FACEBOOK_CONNECT_URL = None
FACEBOOK_CONNECT_DOMAIN = None

# Twitter options
TWITTER_CONSUMER_KEY = None
TWITTER_CONSUMER_SECRET = None


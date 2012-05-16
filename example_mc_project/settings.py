# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2010, 2011, 2012 Participatory Culture Foundation
# 
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
# 
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.

# Example settings for a Miro Community project

import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

USE_SOUTH = bool(os.environ.get('MC_TEST_USE_SOUTH', False))
USE_ES = bool(os.environ.get('MC_TEST_USE_ES', False))

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'example_mc_project.sl3',
    }
}

# Comment these lines out to use a celery server.
CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
# Uncomment and modify these lines to use a celery server
# BROKER_HOST = 'localhost'
# BROKER_PORT = 5672
# BROKER_USER = 'celery'
# BROKER_PASSWORD = 'testing'
# BROKER_VHOST = '/'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

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
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = 'media/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = 'static/'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
# 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'example_mc_project_secret_key'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'uploadtemplate.loader.Loader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
# 'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware'
    'localtv.middleware.FixAJAXMiddleware',
    'localtv.middleware.UserIsAdminMiddleware',
    'openid_consumer.middleware.OpenIDMiddleware',
)

ROOT_URLCONF = 'example_mc_project.urls'

UPLOADTEMPLATE_MEDIA_ROOT = MEDIA_ROOT + 'uploadtemplate/'
UPLOADTEMPLATE_MEDIA_URL = MEDIA_URL + 'uploadtemplate/'
UPLOADTEMPLATE_STATIC_ROOTS = [] # other directories which have static files
UPLOADTEMPLATE_TEMPLATE_ROOTS = [] # other directories with templates

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.comments',
    'django.contrib.flatpages',
    'django.contrib.staticfiles',
    # Uncomment to use south migrations
    # 'south',
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
    'djcelery',
    'notification',
    'socialauth',
    'openid_consumer',
    'voting',
    'daguerre',
    'compressor',
    'mptt',
)

if USE_SOUTH:
    if 'south' not in INSTALLED_APPS:
        INSTALLED_APPS = INSTALLED_APPS + ('south',)
    SOUTH_TESTS_MIGRATE = True

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.request',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
    "localtv.context_processors.localtv",
)

# For debugging, don't redirect mistyped urls
APPEND_SLASH = False


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

FLOWPLAYER_SWF_URL = STATIC_URL + 'localtv/swf/flowplayer-3.2.5.swf'
FLOWPLAYER_JS_URL = STATIC_URL + 'localtv/js/extern/flowplayer-3.2.4.min.js'

CACHE_BACKEND = 'locmem://'

# vimeo keys
VIMEO_API_KEY = None
VIMEO_API_SECRET = None

# UStream key
USTREAM_API_KEY = None

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

# haystack search
if USE_ES:
    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
            'URL': 'http://localhost:9200/',
            'INDEX_NAME': 'mirocommunity'
            }
        }
else:
    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
            'PATH': os.path.join(os.path.dirname(__file__), 'whoosh_index'),
            }
        }

# Facebook options
FACEBOOK_APP_ID = None
FACEBOOK_API_KEY = None
FACEBOOK_SECRET_KEY = None
FACEBOOK_CONNECT_URL = None
FACEBOOK_CONNECT_DOMAIN = None

# Twitter options
TWITTER_CONSUMER_KEY = None
TWITTER_CONSUMER_SECRET = None

from celery.decorators import task
from django.core.mail import mail_admins
from django.core.management import setup_environ
from importlib import import_module
from vidscraper.bulk_import import bulk_import as vs_bulk_import

def setup_django_environment(settings_module):
    mod = import_module(settings_module)
    setup_environ(mod, settings_module)
    from django.conf import settings
    settings._setup()
    from django import db
    db.backend = db.load_backend(settings.DATABASE_ENGINE)
    if db.connection:
        db.connection.close()
    db.connection = db.backend.DatabaseWrapper({
            'DATABASE_HOST': settings.DATABASE_HOST,
            'DATABASE_NAME': settings.DATABASE_NAME,
            'DATABASE_OPTIONS': settings.DATABASE_OPTIONS,
            'DATABASE_PASSWORD': settings.DATABASE_PASSWORD,
            'DATABASE_PORT': settings.DATABASE_PORT,
            'DATABASE_USER': settings.DATABASE_USER,
            'TIME_ZONE': settings.TIME_ZONE,
            })
    db.DatabaseError = db.backend.DatabaseError
    db.IntegrityError = db.backend.IntegrityError
    from django.db.models import query
    from django.db.models.sql import where

    for mod in query, where:
        mod.connection = db.connection


@task()
def bulk_import(settings_module, feed_pk):
    try:
        setup_django_environment(settings_module)
        from localtv.models import Feed
        feed = Feed.objects.get(pk=feed_pk)
        bulk_feed = vs_bulk_import(feed.feed_url)
        feed.update_items(parsed_feed=bulk_feed)
        return feed.video_set.count()
    except:
        import sys, traceback
        mail_admins('Error running bulk_import: %s on %s' % (feed_pk,
                                                           settings_module),
                    '\n'.join(traceback.format_exception(*sys.exc_info())))
        raise

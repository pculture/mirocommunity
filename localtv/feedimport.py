import datetime

from django.forms.fields import slug_re
import feedparser
from lxml.html.clean import clean_html
import vidscraper
from vidscraper.util import clean_description_html

from localtv import util, miroguide_util
from localtv.models import (
    Video, Feed, FEED_STATUS_ACTIVE,
    VIDEO_STATUS_UNAPPROVED, VIDEO_STATUS_ACTIVE,
    CannotOpenImageUrl)


def update_feeds(verbose=False):
    for feed in Feed.objects.filter(status=FEED_STATUS_ACTIVE):
        if feed.auto_approve:
            initial_video_status = VIDEO_STATUS_ACTIVE
        else:
            initial_video_status = VIDEO_STATUS_UNAPPROVED

        parsed_feed = feedparser.parse(feed.feed_url, etag=feed.etag)
        for entry in parsed_feed['entries']:
            if (Video.objects.filter(feed=feed,
                                     guid=entry['guid']).count()
                or Video.objects.filter(feed=feed,
                                        website_url=entry['link']).count()):
                if verbose:
                    print "Skipping %s" % entry['title']
                continue

            file_url = None
            embed_code = None

            video_enclosure = miroguide_util.get_first_video_enclosure(entry)
            if video_enclosure:
                file_url = video_enclosure['href']

            try:
                scraped_data = vidscraper.auto_scrape(
                    entry['link'], fields=['file_url', 'embed'])
                file_url = file_url or scraped_data.get('file_url')
                embed_code = scraped_data.get('embed')
            except vidscraper.errors.Error, e:
                if verbose:
                    print "Vidscraper error: %s" % e

            if not (file_url or embed_code):
                if verbose:
                    print (
                        "Skipping %s because it lacks file_url "
                        "or embed_code") % entry['title']
                continue

            video = Video(
                name=entry['title'],
                site=feed.site,
                description=clean_description_html(entry['summary']),
                file_url=file_url or '',
                embed_code=embed_code or '',
                when_submitted=datetime.datetime.now(),
                when_approved=datetime.datetime.now(),
                status=initial_video_status,
                feed=feed,
                website_url=entry['link'],
                thumbnail_url=miroguide_util.get_thumbnail_url(entry))

            video.save()

            try:
                video.save_thumbnail()
            except CannotOpenImageUrl:
                print "Can't get the thumbnail for %s at %s" % (
                    video.id, video.thumbnail_url)

            if entry.get('tags'):
                entry_tags = [
                    tag['term'] for tag in entry['tags']
                    if len(tag['term']) <= 25
                    and len(tag['term']) > 0
                    and slug_re.match(tag['term'])]
                if entry_tags:
                    tags = util.get_or_create_tags(entry_tags)

                    for tag in tags:
                        video.tags.add(tag)

        feed.etag = parsed_feed.get('etag') or ''
        feed.last_updated = datetime.datetime.now()
        feed.save()

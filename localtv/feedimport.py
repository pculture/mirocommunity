import datetime

from vidscraper import metasearch

from localtv import models, util

def update_feeds(verbose=False):
    for feed in models.Feed.objects.filter(status=models.FEED_STATUS_ACTIVE):
        feed.update_items()


def update_saved_searches(verbose=False):
    for saved_search in models.SavedSearch.objects.all():
        raw_results = metasearch.unfriendlysort_results(
            util.metasearch_from_querystring(
                saved_search.query_string))
        
        for result in raw_results:
            if not result.get('link') or models.Video.objects.filter(
                  site=saved_search.site.site,
                  website_url=result['link']).count():
                continue
            if not (result.get('embed') or result.get('file_url')):
                continue
            
            video = models.Video(
                site=saved_search.site.site,
                name=result['title'],
                description=result.get('description', ''),
                file_url=result.get('file_url', ''),
                website_url=result.get('link', ''),
                thumbnail_url=result.get('thumbnail_url', ''),
                embed_code=result.get('embed'),
                when_submitted=datetime.datetime.now(),
                status=models.VIDEO_STATUS_UNAPPROVED,
                when_approved=datetime.datetime.now())

            video.save()

            if video.file_url:
                video.save_thumbnail()

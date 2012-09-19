import httplib
import urlparse

from vidscraper.utils.mimetypes import is_accepted_type, is_accepted_filename

def is_video_url(url):
    """
    If the URL represents a video file, this function returns True.

    1) It checks the extension to see if it's in VIDEO_EXTENSIONS
    2) It performs an HTTP HEAD request and checks the MIME type with
       is_accepted_type()
    """
    if is_accepted_filename(url):
        return True

    parsed = urlparse.urlparse(url)
    if parsed.scheme == 'http':
        conn = httplib.HTTPConnection(parsed.netloc)
    elif parsed.scheme == 'https':
        conn = httplib.HTTPSConnection(parsed.netloc)
    else:
        return False

    try:
        conn.request('HEAD', parsed.path)
    except IOError:
        # can't connect to the server.
        return False

    response = conn.getresponse()

    mimetype = response.getheader('Content-Type', '')
    return is_accepted_type(mimetype)

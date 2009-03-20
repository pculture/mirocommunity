import sys

PREFERRED_TYPES = [
    'application/x-bittorrent',
    'application/ogg', 'video/ogg', 'audio/ogg',
    'video/mp4', 'video/quicktime', 'video/mpeg',
    'video/x-xvid', 'video/x-divx', 'video/x-wmv',
    'video/x-msmpeg', 'video/x-flv']
PREFERRED_TYPES_ORDER = dict((type, i) for i, type in
        enumerate(PREFERRED_TYPES))

UNSUPPORTED_MIMETYPES = ("video/3gpp", "video/vnd.rn-realvideo", "video/x-ms-asf")


def _has_video_type(enclosure):
    return ('type' in enclosure and
            (enclosure['type'].startswith(u'video/') or
             enclosure['type'].startswith(u'audio/') or
             enclosure['type'] == u"application/ogg" and
            (enclosure['type'] not in UNSUPPORTED_MIMETYPES)))

def _get_enclosure_index(enclosure):
    return PREFERRED_TYPES_ORDER.get(enclosure.get('type'), sys.maxint)

def _get_enclosure_size(enclosure):
    if 'filesize' in enclosure and enclosure['filesize'].isdigit():
        return int(enclosure['filesize'])
    else:
        return -1

def _get_enclosure_bitrate(enclosure):
    if 'bitrate' in enclosure and enclosure['bitrate'].isdigit():
        return int(enclosure['bitrate'])
    else:
        return None

def cmp_enclosures(enclosure1, enclosure2):
    """
    Returns:
      -1 if enclosure1 is preferred, 1 if enclosure2 is preferred, and
      zero if there is no preference between the two of them
    """
    # meda:content enclosures have an isDefault which we should pick
    # since it's the preference of the feed
    if enclosure1.get("isDefault"):
        return -1
    if enclosure2.get("isDefault"):
        return 1

    # let's try sorting by preference
    enclosure1_index = _get_enclosure_index(enclosure1)
    enclosure2_index = _get_enclosure_index(enclosure2)
    if enclosure1_index < enclosure2_index:
        return -1
    elif enclosure2_index < enclosure1_index:
        return 1

    # next, let's try sorting by bitrate..
    enclosure1_bitrate = _get_enclosure_bitrate(enclosure1)
    enclosure2_bitrate = _get_enclosure_bitrate(enclosure2)
    if enclosure1_bitrate > enclosure2_bitrate:
        return -1
    elif enclosure2_bitrate > enclosure1_bitrate:
        return 1

    # next, let's try sorting by filesize..
    enclosure1_size = _get_enclosure_size(enclosure1)
    enclosure2_size = _get_enclosure_size(enclosure2)
    if enclosure1_size > enclosure2_size:
        return -1
    elif enclosure2_size > enclosure1_size:
        return 1

    # at this point they're the same for all we care
    return 0

def getFirstVideoEnclosure(entry):
    """
    Find the first "best" video enclosure in a feedparser entry.
    Returns the enclosure, or None if no video enclosure is found.
    """
    try:
        enclosures = entry.enclosures
    except (KeyError, AttributeError):
        return None

    enclosures = [e for e in enclosures if _has_video_type(e)]
    if len(enclosures) == 0:
        return None

    enclosures.sort(cmp_enclosures)
    return enclosures[0]

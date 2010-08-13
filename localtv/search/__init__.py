import shlex
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from haystack.query import SearchQuerySet, SQ

from tagging.models import Tag
from localtv.models import Feed, Category, SavedSearch
from localtv.playlists.models import Playlist

def tokenize(query):
    or_stack = []
    negative = False
    if isinstance(query, unicode):
        # FIXME: ignores characters not in latin-1 since shlex doesn't handle
        # them
        while True:
            try:
                query = query.encode('latin-1')
                break
            except UnicodeEncodeError, e:
                # strip offending characerers
                query = query[:e.start] + query[e.end:]
    while query:
        try:
            lex = shlex.shlex(query, posix=True)
            lex.commenters = '' # shlex has a crazy interface
            lex.wordchars = lex.wordchars + '-:/'
            tokens = list(lex)
            break
        except ValueError, e:
            if e.args[0] == 'No closing quotation':
                # figure out what kind of quote we missed
                double_count = sum(1 for c in query if c == '"')
                if double_count % 2: # odd
                    index = query.rfind('"')
                else:
                    index = query.rfind("'")
                query = query[:index] + query[index+1:]

    for token in tokens:
        if token == '-':
            if not or_stack:
                if negative:
                    negative = False
                else:
                    negative = True
        elif token == '{':
            negative = False
            or_stack.append([])
        elif token == '}':
            negative = False
            last_or = or_stack.pop()
            if not or_stack:
                yield last_or
            else:
                or_stack[-1].append(last_or)
        else:
            if token[0] in '\'"':
                token = token[1:-1]
            if negative and isinstance(token, basestring):
                negative = False
                token = '-' + token
            token = token.decode('latin-1')
            if or_stack:
                or_stack[-1].append(token)
            else:
                yield token
    while or_stack:
        yield or_stack.pop()

def _get_object(model, token, *fields):
    """
    Tries various fields to get an object.
    """
    default_kwargs = {}
    try:
        model._meta.get_field_by_name('site')
    except Exception:
        pass
    else:
        default_kwargs['site'] = Site.objects.get_current()
    if 'pk' not in fields:
        fields = fields + ('pk',)

    for field in fields:
        methods = ['exact']
        if field != 'pk':
            methods.append('iexact')
        for method in methods:
            kwargs = default_kwargs.copy()
            kwargs['%s__%s' % (field, method)] = token
            try:
                return model.objects.get(**kwargs)
            except (model.DoesNotExist, ValueError):
                pass

def _tokens_to_sqs(tokens, sqs):
    """
    Turns a list of tokens and a SearchQuerySet into a SQS representing those
    tokens.
    """
    clean = sqs.query.clean
    for token in tokens:
        if isinstance(token, basestring):
            method = sqs.filter
            negative = False
            if token[0] == '-':
                negative = True
                method = sqs.exclude
                token = token[1:]
            if ':' not in token:
                sqs = method(content=clean(token))
            else:
                # possibly a special keyword
                keyword, rest = token.split(':', 1)
                keyword = keyword.lower()
                if keyword == 'category':
                    category = _get_object(Category, rest,
                                           'name', 'slug', 'pk')
                    if category is not None:
                        sqs = method(categories=category.pk)
                elif keyword == 'feed':
                    feed = _get_object(Feed, rest,
                                       'name', 'pk')
                    if feed is not None:
                        sqs = method(feed=feed.pk)
                elif keyword == 'search':
                    search = _get_object(SavedSearch, rest,
                                         'query_string', 'pk')
                    if search is not None:
                        sqs = method(search=search.pk)
                elif keyword == 'tag':
                    tag = _get_object(Tag, rest, 'name')
                    if tag is not None:
                        sqs = method(tags=tag)
                elif keyword == 'user':
                    user = _get_object(User, rest,
                                       'username', 'pk')
                    if user is not None:
                        if not negative:
                            sqs = sqs.filter(SQ(user=user.pk) |
                                             SQ(authors=user.pk))
                        else:
                            sqs = sqs.exclude(user=user.pk).exclude(
                                    authors=user.pk)
                elif keyword == 'playlist':
                    playlist = _get_object(Playlist, rest, 'pk')
                    if playlist is None and '/' in rest:
                        # user/slug
                        user, slug = rest.split('/', 1)
                        try:
                            playlist = Playlist.objects.get(
                                user__username=user,
                                slug=slug)
                        except Playlist.DoesNotExist:
                            pass
                    if playlist is not None:
                        sqs = method(playlists=playlist.pk)
                else:
                    sqs = method(content=clean(token))
        else:
            # or block
            clone = sqs._clone()
            for or_token in token:
                sqs = sqs | _tokens_to_sqs([or_token], clone)

    return sqs

def auto_query(query, sqs=None):
    """
    Turn the given SearchQuerySet into something representing query.
    """
    if sqs is None:
        sqs = SearchQuerySet()
    return _tokens_to_sqs(tokenize(query), sqs)

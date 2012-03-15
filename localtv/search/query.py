# This file is part of Miro Community.
# Copyright (C) 2010 Participatory Culture Foundation
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

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from haystack.query import SearchQuerySet, SQ

from tagging.models import Tag
from localtv.models import Feed, Category, SavedSearch
from localtv.playlists.models import Playlist
from localtv.search import shlex


class SmartSearchQuerySet(SearchQuerySet):
    """
    Implements an auto_query method which supports the following keywords on
    top of :class:`haystack.query.SearchQuerySet`\ 's basic functionality:

    * playlist:#
    * playlist:user/slug
    * category:#
    * category:name
    * category:slug
    * user:#
    * user:username
    * feed:#
    * feed:name
    * search:#
    * search:query string
    * tag:name
    * {one of these terms}
    * -"not this term"

    """
    def tokenize(self, query):
        or_stack = []
        negative = False

        while query:
            try:
                lex = shlex.shlex(query, posix=True, locale=True)
                lex.commenters = '' # shlex has a crazy interface
                lex.wordchars = u'-:/_'
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
                else:
                    raise

        if not query:
            raise StopIteration

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
                if or_stack:
                    or_stack[-1].append(token)
                else:
                    yield token
        while or_stack:
            yield or_stack.pop()

    def _get_object(self, model, token, *fields):
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

    def _tokens_to_sqs(self, tokens, sqs):
        """
        Turns a list of tokens and a SearchQuerySet into a SQS representing
        those tokens.

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
                        category = self._get_object(Category, rest,
                                               'name', 'slug', 'pk')
                        if category is not None:
                            sqs = method(categories=category.pk)
                    elif keyword == 'feed':
                        feed = self._get_object(Feed, rest,
                                           'name', 'pk')
                        if feed is not None:
                            sqs = method(feed=feed.pk)
                    elif keyword == 'search':
                        search = self._get_object(SavedSearch, rest,
                                             'query_string', 'pk')
                        if search is not None:
                            sqs = method(search=search.pk)
                    elif keyword == 'tag':
                        tag = self._get_object(Tag, rest, 'name')
                        if tag is not None:
                            sqs = method(tags__contains=tag.pk)
                    elif keyword == 'user':
                        user = self._get_object(User, rest,
                                           'username', 'pk')
                        if user is not None:
                            if not negative:
                                sqs = sqs.filter(SQ(user=user.pk) |
                                                 SQ(authors=user.pk))
                            else:
                                sqs = sqs.exclude(user__exact=user.pk).exclude(
                                        authors=user.pk)
                    elif keyword == 'playlist':
                        playlist = self._get_object(Playlist, rest, 'pk')
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
                            sqs = method(playlists__contains=playlist.pk)
                    else:
                        sqs = method(content=clean(token))
            else:
                # or block
                clone = sqs._clone()
                for or_token in token:
                    sqs = sqs | clone._tokens_to_sqs([or_token], clone)

        return sqs

    def auto_query(self, query_string):
        """
        Performs a best guess constructing the search query.

        """
        return self._tokens_to_sqs(self.tokenize(query_string), self)

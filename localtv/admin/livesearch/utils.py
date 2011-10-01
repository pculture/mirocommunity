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


import re


WHITESPACE_RE = re.compile('\s+')


def parse_querystring(querystring):
    """
    Returns a ``(include_terms, exclude_terms)`` tuple. Currently extremely
    naive.

    """
    terms = set(querystring.split())
    exclude_terms = set((term for term in terms if term.startswith('-')))
    include_terms = terms - exclude_terms
    stripped_exclude_terms = [term.lstrip('-') for term in exclude_terms]
    return include_terms, stripped_exclude_terms


def terms_for_cache(include_terms, exclude_terms):
        terms_as_str = u''.join(include_terms) + u''.join(exclude_terms)
        return WHITESPACE_RE.sub('', terms_as_str)

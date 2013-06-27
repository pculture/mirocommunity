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

import shlex

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
            lex.wordchars = lex.wordchars + '-:'
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

def auto_query(sqs, query):
    """
    Turn the given SearchQuerySet into something representing query.
    """
    return sqs.auto_query(query)

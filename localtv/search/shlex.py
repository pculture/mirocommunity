# -*- coding: iso-8859-1 -*-
"""A lexical analyzer class for simple shell-like syntaxes."""

# Module and documentation by Eric S. Raymond, 21 Dec 1998
# Input stacking and error message cleanup added by ESR, March 2000
# push_source() and pop_source() made explicit by ESR, January 2001.
# Posix compliance, split(), string arguments, and
# iterator interface by Gustavo Niemeyer, April 2003.
# Support for Unicode characters, Paul Swartz, August 2010

# PKS: I removed a bunch of stuff we don't need for MC

import logging

from collections import deque

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

__all__ = ["shlex"]

class shlex:
    "A lexical analyzer class for simple shell-like syntaxes."
    def __init__(self, instream, posix=True, locale=False):
        self.was_unicode = False
        if isinstance(instream, basestring):
            if isinstance(instream, unicode):
                self.was_unicode = True
                instream = instream.encode('utf_32_be')
            instream = StringIO(instream)
        self.instream = instream
        self.locale = locale
        self.posix = posix
        if posix:
            self.eof = None
        else:
            self.eof = ''
        self.commenters = '#'
        if locale:
            self.wordchars = ''
            self.whitespace = ''
        else:
            self.wordchars = ('abcdfeghijklmnopqrstuvwxyz'
                              'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')
            if self.posix:
                self.wordchars += ('ßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ'
                                   'ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ')
            self.whitespace = ' \t\r\n'
        self.whitespace_split = False
        self.quotes = '\'"'
        self.escape = '\\'
        self.escapedquotes = '"'
        if self.was_unicode:
            self.wordchars = self.wordchars.decode('latin1')
            self.whitespace = self.whitespace.decode('latin1')
            self.quotes = self.quotes.decode('latin1')
            self.escape = self.quotes.decode('latin1')
            self.escapedquotes = self.escapedquotes.decode('latin1')
        self.state = ' '
        self.pushback = deque()
        self.lineno = 1
        self.debug = 0
        self.token = ''
        logging.debug('shlex: reading from %s, line %d',
                      self.instream, self.lineno)

    def push_token(self, tok):
        "Push a token onto the stack popped by the get_token method"
        logging.debug("shlex: pushing token %r", tok)
        self.pushback.appendleft(tok)

    def get_token(self):
        "Get a token from the input stream (or from stack if it's nonempty)"
        if self.pushback:
            tok = self.pushback.popleft()
            logging.debug("shlex: popping token %r", tok)
            return tok
        # No pushback.  Get a token.
        raw = self.read_token()
        # Maybe we got EOF instead?
        while raw == self.eof:
            return self.eof
        # Neither inclusion nor EOF
        if raw != self.eof:
            logging.debug("shlex: token=%r", raw)
        else:
            logging.debug("shlex: token=EOF")
        return raw

    def read_token(self):
        quoted = False
        escapedstate = ' '
        while True:
            if not self.was_unicode:
                nextchar = self.instream.read(1)
            else:
                nextchar = self.instream.read(4).decode('utf_32_be')
            if nextchar == '\n':
                self.lineno = self.lineno + 1
            if self.debug >= 3:
                logging.debug("shlex: in state %r I see character: %r",
                              self.state, nextchar)
            if self.state is None:
                self.token = ''        # past end of file
                break
            elif self.state == ' ':
                if not nextchar:
                    self.state = None  # end of file
                    break
                elif nextchar in self.whitespace or \
                        self.locale and nextchar.isspace():
                    logging.debug(
                        "shlex: I see whitespace in whitespace state")
                    if self.token or (self.posix and quoted):
                        break   # emit current token
                    else:
                        continue
                elif nextchar in self.commenters:
                    self.instream.readline()
                    self.lineno = self.lineno + 1
                elif self.posix and nextchar in self.escape:
                    escapedstate = 'a'
                    self.state = nextchar
                elif nextchar in self.wordchars or \
                        self.locale and nextchar.isalnum():
                    self.token = nextchar
                    self.state = 'a'
                elif nextchar in self.quotes:
                    if not self.posix:
                        self.token = nextchar
                    self.state = nextchar
                elif self.whitespace_split:
                    self.token = nextchar
                    self.state = 'a'
                else:
                    self.token = nextchar
                    if self.token or (self.posix and quoted):
                        break   # emit current token
                    else:
                        continue
            elif self.state in self.quotes:
                quoted = True
                if not nextchar:      # end of file
                    logging.debug("shlex: I see EOF in quotes state")
                    # XXX what error should be raised here?
                    raise ValueError, "No closing quotation"
                if nextchar == self.state:
                    if not self.posix:
                        self.token = self.token + nextchar
                        self.state = ' '
                        break
                    else:
                        self.state = 'a'
                elif self.posix and nextchar in self.escape and \
                     self.state in self.escapedquotes:
                    escapedstate = self.state
                    self.state = nextchar
                else:
                    self.token = self.token + nextchar
            elif self.state in self.escape:
                if not nextchar:      # end of file
                    logging.debug("shlex: I see EOF in escape state")
                    # XXX what error should be raised here?
                    raise ValueError, "No escaped character"
                # In posix shells, only the quote itself or the escape
                # character may be escaped within quotes.
                if escapedstate in self.quotes and \
                   nextchar != self.state and nextchar != escapedstate:
                    self.token = self.token + self.state
                self.token = self.token + nextchar
                self.state = escapedstate
            elif self.state == 'a':
                if not nextchar:
                    self.state = None   # end of file
                    break
                elif nextchar in self.whitespace or \
                        self.locale and nextchar.isspace():
                    logging.debug("shlex: I see whitespace in word state")
                    self.state = ' '
                    if self.token or (self.posix and quoted):
                        break   # emit current token
                    else:
                        continue
                elif nextchar in self.commenters:
                    self.instream.readline()
                    self.lineno = self.lineno + 1
                    if self.posix:
                        self.state = ' '
                        if self.token or (self.posix and quoted):
                            break   # emit current token
                        else:
                            continue
                elif self.posix and nextchar in self.quotes:
                    self.state = nextchar
                elif self.posix and nextchar in self.escape:
                    escapedstate = 'a'
                    self.state = nextchar
                elif nextchar in self.wordchars or nextchar in self.quotes \
                    or self.whitespace_split or \
                    self.locale and nextchar.isalnum():
                    self.token = self.token + nextchar
                else:
                    self.pushback.appendleft(nextchar)
                    logging.debug("shlex: I see punctuation in word state")
                    self.state = ' '
                    if self.token:
                        break   # emit current token
                    else:
                        continue
        result = self.token
        self.token = ''
        if self.posix and not quoted and result == '':
            result = None
        if result:
            logging.debug("shlex: raw token=%r", result)
        else:
            logging.debug("shlex: raw token=EOF")
        return result

    def __iter__(self):
        return self

    def next(self):
        token = self.get_token()
        if token == self.eof:
            raise StopIteration
        return token

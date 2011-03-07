# Copyright 2011 - Participatory Culture Foundation
#
# This file is part of Miro Community.
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

### FIXME
# This file should get moved out into its own Python package.
###

import httplib2
import urllib
from xml.dom.minidom import Document

from django.conf import settings

def generate_ticket_body(subject_text, body_text, requester_email_text):
    doc = Document()
    # Create the outer ticket element
    ticket = doc.createElement("ticket")
    doc.appendChild(ticket)

    # Create the other data
    subject = doc.createElement('subject')
    subject.appendChild(doc.createTextNode(subject_text))
    ticket.appendChild(subject)

    requester = doc.createElement('requester-email')
    requester.appendChild(doc.createTextNode(requester_email_text))
    ticket.appendChild(requester)

    description = doc.createElement('description')
    description.appendChild(doc.createTextNode(body_text))
    ticket.appendChild(description)

    return doc.toxml()

outbox = []    

def create_ticket(subject, body, requester_email='paulproteus+robot@pculture.org'):
    global outbox

    h= httplib2.Http("/tmp/.cache")
    if getattr(settings, "ZENDESK_USERNAME"):
        h.add_credentials(getattr(settings, 'ZENDESK_USERNAME'),
                          getattr(settings, 'ZENDESK_PASSWORD'))
    else:
        raise ValueError, "Cannot create ticket because Zendesk not configured. Bailing out now."

    # Prepare kwargs for HTTP request
    kwargs = dict(headers={'Content-Type': 'application/xml'},
                  body=(generate_ticket_body(subject, body, requester_email)))

    # If we are inside the test suite, just create an "outbox" and push things onto it
    # Detect the test suite by looking at the email backend
    if settings.EMAIL_BACKEND == 'django.core.mail.backends.locmem.EmailBackend':
        outbox.append(kwargs)
        return True

    # Oh, so we're in real mode? Okay, then let's actually do the HTTP game.
    response = h.request("http://mirocommunity.zendesk.com/tickets.xml", "POST", **kwargs)
    if response[0]['status'] == '201':
        return True
    return False

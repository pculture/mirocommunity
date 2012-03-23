Reporting bugs and requesting features
======================================

One of the easiest ways you can help Miro Community is to put tickets into the
`bug tracker`_, either reporting bugs or asking for new features.

Reporting bugs
++++++++++++++

Here are some guidelines for good bug reports:

* Check the bug tracker to make sure that the bug has not already been
  reported.

* Ask on the IRC channel (`#miro-hackers on irc.freenode.net
  <irc://irc.freenode.net/miro-hackers>`_) or the `mailing list`_ to make
  sure that what you're seeing really is a bug.

* Make sure that the bug is reproducible. Include instructions for how to
  reproduce it.

* Be as specific as possible. If a video page looks strange, check whether
  other video pages also look strange, then report which is the case.

* Give as much information as possible. Include error text, screenshots,
  links, anything that you have.

The better your bug report, the more likely someone is to fix it!

.. _bug tracker: http://bugzilla.pculture.org/
.. _mailing list: http://groups.google.com/group/miro-community-development

Reporting security issues
-------------------------

Please report security issues *only* to dev@mirocommunity.org.

Requesting features
+++++++++++++++++++

When requesting a new feature, please do the following:

* Ask on the IRC channel (#miro-hackers on FreeNode) or the `mailing list`_
  to get a general feeling on the feature.

* In your ticket, give a clear use case for/reason behind the new feature.

.. _ticket-life-cycle:

Ticket life cycle
+++++++++++++++++

* New tickets can be claimed by any community member.

* New and assigned tickets may be ``RESOLVED`` by a core member at any
  time with the following resolutions:

  * ``INVALID``: The ticket isn't applicable to Miro Community. For
    example, someone suggesting a change to Django.
  * ``WONTFIX``: The ticket will not be accepted, probably because it is
    not a bug, because the payoff is not seen as worth the effort, or
    because the ticket is rendered obsolete by parallel work on another
    ticket.
  * ``DUPLICATE``: The ticket is already in the tracker.
  * ``WORKSFORME``: The ticket would be a valid bug, but it can't be
    reproduced.
  * ``INCOMPLETE``: More information is required to confirm the bug or explain
    the feature.

* Once a ticket is claimed, it is up to the assignee to start a branch for
  that ticket and submit a pull request to the canonical repository. When
  a pull request is submitted, the assignee should set the ticket's
  ``needs-peer-review`` flag to ``?`` and link to the pull request.

* Once a pull request has been submitted and the ticket has been flagged, a
  core member will review the code. This should be someone other than the
  assignee. If there are problems with the branch, they should explain the
  problems by commenting on github, inline and on the pull request.
  Otherwise, they can merge it in and change the ticket status to
  ``RESOLVED/FIXED`` and the ``needs-peer-review`` flag to ``+``.
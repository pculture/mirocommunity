Contributing Code
=================

You want to contribute code? Great! Here's how you can do it.

Finding tickets
+++++++++++++++

Our tickets are all stored in our `bugzilla installation`_; you can browse the
tickets by component, or check out this `summary of all open tickets`__.

.. _bugzilla installation: http://bugzilla.pculture.org/
__ http://bugzilla.pculture.org/buglist.cgi?query_format=advanced&list_id=2600&component=Admin&component=Backend&component=Custom%20Theming&component=Documentation&component=Frontpage&component=Listings&component=Source%20Imports&component=Submission&component=View%20Video&resolution=---&product=Miro%20Community

Claiming tickets
++++++++++++++++

If you don't see a ticket, feel free to open one! Any ticket that is assigned
to admin@pculture.org is free to claim without asking, simply by assigning it
to yourself. If a ticket is already claimed, but seems inactive, contact the
assignee and see if it's all right for you to claim it. (Relatedly, if you
don't actually have time to work on a ticket, don't claim it!)

Writing code
++++++++++++

We use the `same coding style as the Django project`__.

__ https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/coding-style/

Submitting code
+++++++++++++++

We accept code submissions as pull requests to our `github repository`__, not
as patch files, diff files, or anything else. Most of the time, when you submit
code, it will be as a :doc:`ticket branch </internals/branching-model>` - though if the
change is extremely minor, you can submit a pull request without opening a
ticket first. Pull requests must include any changes to unit tests and
:doc:`documentation <documentation>` that are needed.

__ http://github.com/pculture/mirocommunity

Before we can accept your code submission, you will need to sign a
:download:`Contributor Assignment Agreement </downloads/PCF__Contributor_Assignment_Agreement.pdf>`,
digitize it with a scanner or a good camera, and send it to legal@pculture.org.
It's super easy, and it lets us keep the project open source.

Review process
++++++++++++++

After the pull request is made, a core contributor to the Miro Community
project will review the code; they will either accept the pull request or
point out where changes need to be made to get the branch ready for acceptance.

.. seealso:: :ref:`ticket-life-cycle`
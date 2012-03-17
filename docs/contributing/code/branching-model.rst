Git Branching Model
===================

We use a variant of `nvie's git branching model`_ for our workflow.

.. _nvie's git branching model: http://nvie.com/posts/a-successful-git-branching-model/

The following main branches exist:

* ``master`` always points to the latest stable release. Any merge into
  master must represent a stable release as far as we can tell.
* ``develop`` always points to the latest development code. This should
  theoretically always be production-ready, but that is not guaranteed.

There are also some "supporting branch" types. Any supporting branch must
be reviewed before being merged.

* Release branches. Naming convention: ``release/<version_number>``. These
  branches originate from the development branch and may only receive
  bugfixes for release blockers. Essentially, they represent release
  candidates. The release branch should be merged back into the
  ``develop`` branch on a regular basis. When the release candidate is
  accepted, it will be merged into the master branch and the development
  branch. The master branch merge commit will be tagged with the new
  version number.

* Hotfix branches. Naming convention: ``hotfix/<ticket_number>``. These
  branches represent *severe bugs* in the master branch. They originate
  from the master branch and fix a specific issue. Once checked and
  confirmed, they are merged into the master branch as a new point
  release, as well as being merged into the current release branch, or
  the development branch if no release is under way.

* Feature branches. Naming convention: ``feature/<short_description>``.
  These branches represent large new features - for example, a large
  refactor or major UI change. Feature branches may only originate from
  the ``develop`` branch and may only be merged into the ``develop``
  branch.

* Ticket branches. Naming convention: ``ticket/<ticket_number>``. These
  branches represent tickets from the bug tracker which are not severe
  bugs in the master branch, and which have non-trivial solutions. Ticket
  branches may originate from ``develop``, a feature branch (if the
  ticket is specific to that feature) or a release branch (if the ticket
  is a release blocker). They are merged into the branch they originated
  from.

  Trivial fixes to tickets can be made directly to the relevant branch,
  and should include the ticket number prominently in the commit message.
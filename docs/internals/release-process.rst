Release process
===============

Version numbering
+++++++++++++++++

Miro Community numbers its versions as ``A.B`` or ``A.B.C``.

* ``A`` is the `major` version number. This is incremented for broad, sweeping changes to Miro Community - for example, a refactor of the entire admin.
* ``B`` is the `minor` version number. This is incremented for new features which aren't broad, sweeping changes to Miro Community
* ``C`` is the `micro` version number. This is incremented for bug and security fixes.

Major releases
--------------

Very infrequent. May represent large changes.

Minor releases
--------------

The goal is to have minor releases on a fairly regular basis, every couple of months. Minor releases can add new features and remove features from previous releases.

Micro releases
--------------

Micro releases may not introduce new features; they may only fix critical issues:

* Security issues.
* Data loss.
* Crashing bugs/500 errors.
* Major bugs in new features from the latest minor release.

These bug fixes will be collected in a release branch; once all reported bugs have been resolved, the branch will be released. The one exception to this is security fixes, which cause the branch to be released immediately.


Release process
+++++++++++++++

Alpha (development)
----------------------

In this phase, features can be added to the upcoming release, with the approval of a core developer. Features with working patches are much more likely to be accepted than features with a thought-out design, which in turn are more likely to be accepted than off-hand suggestions.

Features will be marked on the following scale:

1. P1: Must have. The release can't happen without this.
2. P2: Should have. This would be good to have in the release.
3. P3: Maybe. This would be nice, but we don't need it.

Any features which are lower priority than that should be marked to the ``future`` milestone.

Bugs can also be added to the upcoming release, or marked ``RESOLVED/WONTFIX`` if an accepted P1 feature renders the bug irrelevant.

Micro releases do not have this phase.

Beta (bugfixes)
---------------

Features can no longer be added in this phase; this corresponds to the creation of a release branch. Any bugs which are rendered irrelevant by features which have made it in should be marked ``RESOLVED/WONTFIX``.

Bugs can still be added to the upcoming release; bugs with patches are much more likely to be resolved.

Before this stage can end, all bugs which have been marked ``RESOLVED/FIXED`` must be verified and marked ``VERIFIED/FIXED``.

Release candidate (blockers)
----------------------------

In this phase, the only bugfixes that will be addressed are critical issues:

* Security issues.
* Data loss.
* Crashing bugs/500 errors.
* Major bugs in new features introduced in this release.

Before this stage can end, all bugs which have been marked ``RESOLVED/FIXED`` must be verified and marked ``VERIFIED/FIXED``.

Once this stage ends, the release will be merged into ``master`` and tagged with the new version number.

Support
+++++++

Only the latest minor release will be supported with micro releases, all of which will be merged into the ``develop`` branch as well.
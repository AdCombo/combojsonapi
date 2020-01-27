Contributing
************
First off, thank you for considering contributing to ComboJSONAPI. It's people
like you that make ComboJSONAPI such a great tool.

Where do I go from here?
========================
If you've noticed a bug or have a question that doesn't belong on the `search the issue tracker`_ to see if someone else in
the community has already created a ticket. If not, go ahead and `make one`_!

Fork & create a branch
======================

If this is something you think you can fix, then `fork ComboJSONAPI`_ and create
a branch with a descriptive name.

A good branch name would be (where issue #325 is the ticket you're working on):

:code:`git checkout -b 325-add-japanese-translations`

Get the test suite running
==========================

Make sure you're using a recent pytest

:code:`pytest -s -vv tests`

Did you find a bug?
===================

* **Ensure the bug was not already reported** by `searching all issues`_.

* If you're unable to find an open issue addressing the problem,
  `open a new one`_. Be sure to include a **title and clear
  description**, as much relevant information as possible, and a **code sample**
  or an **executable test case** demonstrating the expected behavior that is not
  occurring.

Implement your fix or feature
=============================

At this point, you're ready to make your changes! Feel free to ask for help;
everyone is a beginner at first :smile_cat:

Get the style right
===================

Your patch should follow the same conventions & pass the same code quality
checks as the rest of the project. :code:`flake8` will give you feedback in
this regard.

Add a changelog entry
=====================

If your PR includes user-observable changes, you'll be asked to add a changelog
entry following the existing changelog format.

The changelog format is the following:

* One line per PR describing your fix or enhancement.
* Entries end with a dot, followed by "[#pr-number] by [@github-username]".
* Entries are added under the "Unreleased" section at the top of the file, under
  the "Bug Fixes" or "Enhancements" subsection.
* References to github usernames and pull requests use `shortcut reference links`_.
* Your github username reference definition is included in the correct
  alphabetical position at the bottom of the file.

Make a Pull Request
===================

At this point, you should switch back to your master branch and make sure it's
up to date with ComboJSONAPI's master branch:

.. code:: sh

    git remote add upstream git@github.com:AdCombo/ComboJSONAPI.git
    git checkout master
    git pull upstream master

Then update your feature branch from your local copy of master, and push it!

.. code:: sh

    git checkout 325-add-japanese-translations
    git rebase master
    git push --set-upstream origin 325-add-japanese-translations

Finally, go to GitHub and `make a Pull Request`_ :D

Keeping your Pull Request updated
=================================

If a maintainer asks you to "rebase" your PR, they're saying that a lot of code
has changed, and that you need to update your branch so it's easier to merge.

To learn more about rebasing in Git, there are a lot of `good`_
`resources`_ but here's the suggested workflow:


.. code:: sh

    git checkout 325-add-japanese-translations
    git pull --rebase upstream master
    git push --force-with-lease 325-add-japanese-translations

Merging a PR (maintainers only)
===============================

A PR can only be merged into master by a maintainer if it:

* passes CI;
* has been approved by at least two maintainers. If author is a maintainer who
  opened the PR, only one extra approval is needed;
* has no requested changes;
* is up to date with current master;
* has comments and commit messages written in English only.

Any maintainer is allowed to merge a PR if all of these conditions are
met.

Shipping a release (maintainers only)
=====================================

Maintainers need to do the following to push out a release:

* Make sure all pull requests are in and that changelog is current
* Update :code:`version.rb` file and changelog with new version number
* If it's not a patch level release, create a stable branch for that release,
  otherwise switch to the stable branch corresponding to the patch release you
  want to ship:


.. code:: sh

    git checkout master
    git fetch ComboJSONAPI
    git rebase ComboJSONAPI/master
    # If the release is 2.1.x then this should be: 2-1-stable
    git checkout -b N-N-stable
    git push ComboJSONAPI N-N-stable:N-N-stable


.. _`chandler`: https://github.com/mattbrictson/chandler#2-configure-credentials
.. _`good`: http://git-scm.com/book/en/Git-Branching-Rebasing
.. _`resources`: https://help.github.com/articles/interactive-rebase
.. _`make a Pull Request`: https://github.github.com/gfm/#shortcut-reference-link
.. _`shortcut reference links`: https://github.github.com/gfm/#shortcut-reference-link
.. _`fork ComboJSONAPI`: https://help.github.com/articles/fork-a-repo
.. _`searching all issues`: https://github.com/AdCombo/issues?q=
.. _`open a new one`: https://github.com/AdCombo/combojsonapi/issues/new
.. _`search the issue tracker`: https://github.com/AdCombo/combojsonapi/issues?q=something
.. _`make one`: https://github.com/AdCombo/combojsonapi/issues/new

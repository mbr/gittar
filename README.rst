gittar
======

Gittar creates a git commit from a directory or an archive, allowing you to
store a sequence of selective filesystem-snapshots as git commits.


Why?
----

The initial use case for ``gittar`` was storing a compiled version of an
application in a seperate root inside a git repository. Here's an example:

Assume you have a webapplication that needs to compile its assets before being
deployed. You do not want to have to install a lot of LESS or JS compilers, CSS
minifiers, etc. on your production environment.

First, you run your build tool (e.g. ``scons`` when using `the scons-tools web
module <https://github.com/mbr/scons-tools>`_), now your app is inside the
directory ``myapp``, including the compiled static files, while the source
files reside outside the ``myapp`` directory.

Now, you can run::

  gittar -b web file:///`pwd`/myapp

This will create a new commit containing everything inside the ``myapp``
directory. If the branch ``web`` does not exist, it will be created and will
point to the new commit, which will have no parent. If the branch did exist
before, the new commit will have it as a parent and the branch will be updated.

A simple application for this is deploying to `heroku <http://heroku.com>`_.
Build your app, add a new ``gittar``-commit to the web branch and push it using
``git push heroku web:master``.

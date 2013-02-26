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

  gittar -b web file:myapp

This will create a new commit containing everything inside the ``myapp``
directory. If the branch ``web`` does not exist, it will be created and will
point to the new commit, which will have no parent. If the branch did exist
before, the new commit will have it as a parent and the branch will be updated.

The hash of the new commit will be printed to stdout. If the ``-b`` option is
not specified, this is the only way to reach the commit.

A simple application for this is deploying to `heroku <http://heroku.com>`_.
Build your app, add a new ``gittar``-commit to the web branch and push it using
``git push heroku web:master``.


Schemes
-------

``gittar`` can add files from ZIP-Archives, tar-Archives or plain directories
and files.

All sources for inclusion are specified using the following syntax::

  scheme:arg1:arg2:...:named_arg1=value1:named_arg2=value2:...

A scheme is one of ``file``, ``zip`` or ``tar``. The arguments and named
arguments are passed on to the sources collecting the files and have meanings
depending on the scheme.

Multiple schemes can be specified in a single command.

The file-scheme
~~~~~~~~~~~~~~~

A single file or a directory can be added as follows::

  gittar file:myfile file:/my/home/special_file file:/some/directory

This will add ``myfile`` to the commit with the path ``myfile``. The file
``/my/home/special_file`` will also be added, but named ``special_file`` (no
path) inside the commit.

Assuming ``/some/directory`` is a directory, all files in it will be added
recursively, without the ``/some/`` path prefix. Example: A file
``/some/directory/foo/bar`` will be added as ``directory/foo/bar`` to the
commit.

Similarities and differences to tar
"""""""""""""""""""""""""""""""""""

Specifying ``file:`` targets is similiar to tar, with one key differences:
Instead of adding absolute paths, ``gittar`` will strip any path information
(but keep subdirectory trees intact).

Specifically, ``gittar`` will never change pathnames depending on your current
working directory.

Wildcards and directories as root
"""""""""""""""""""""""""""""""""

Since directories are added recursively and always kept in the relative path,
it's not possible this way to add a directory as the root. One solution is to
use wildcards (note the quotes to prevent wildcard expansion by the shell)::

  gittar 'file:/some/directory/*'

If there are three files in ``/some/directory`` named ``a_file``, ``a_dir`` and
``foo``, the command above will be logically expanded to::

  gittar 'file:/some/directory/a_file' 'file:/some/directory/a_dir' 'file:/some/directory/foo'

This will result in ``a_file`` being added to the root of the commit.

Note that wildcard-expansion is done UNIX-style using the ``glob`` module.
Files starting with a dot (``.``) are not included using ``*``. To add all
files in a directory ``/foo`` and not having them as subdirectories, you need
to use the following command::

  gittar 'file:/foo/*' 'file:/foo/.*'

The zip-scheme
~~~~~~~~~~~~~~

Adds the contents of a zip-Archive::

  gittar zip:/path/to/some/archive.zip

This will add all files inside ``/path/to/some/archive.zip`` with their
relative paths to the commit.

The tar-scheme
~~~~~~~~~~~~~~

Works fairly similiar to the ``zip``-scheme, but for tar archives. Automatic
detection of compression is done. Example::

  gittar tar:somearchive.tar tar:/another/archive.tar.bz2


Common Options
--------------

Extra options can be specififed, some are valid for all sources.

Inclusion/Exclusion
~~~~~~~~~~~~~~~~~~~

The ``include`` and ``exclude`` options can be used to specify which files
should be included in the commit. Example::

  gittar tar:myarchive.tar:include=*.css:include=output/*.html:exclude=*~

Note: You will most likely have to enter this with backslash-escaped asterisks
(``\*``) on your shell.

The command above will include all CSS files and all HTML files from the output
folder, provided they do not end in a tilde``~``.

If no include option is given all not-excluded files are included.

Regular expressions
~~~~~~~~~~~~~~~~~~~

The ``include`` and ``exclude`` commands use UNIX shell patterns. You can use
python (Perl-like) regular expressions by using ``rinclude`` and ``rexclude``
instead.

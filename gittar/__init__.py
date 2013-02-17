#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import stat
import time
from urlparse import urlparse
import sys

from dateutil.tz import tzlocal
from datetime import datetime

from dulwich.repo import Repo
from dulwich.objects import Blob, Tree, Commit, parse_timezone

SOURCES = {}


def gittar_url(s):
    r = urlparse(s)

    if not r.scheme in SOURCES:
        raise ValueError('Schema %r not known' % r.scheme)

    return r


def get_local_tz_offset(ltz, now):
    offset = ltz.utcoffset(now)
    seconds = offset.seconds
    sign = '-' if seconds < 0 else '+'
    offset = abs(offset)

    return offset.days * 24 * 60 * 60 + offset.seconds, False


now = int(time.time())
localtz = get_local_tz_offset(tzlocal(), datetime.utcfromtimestamp(now))
parser = argparse.ArgumentParser()
parser.add_argument('sources', nargs='+', type=gittar_url,
                    metavar='SCHEMA://SOURCE',
                    help='Sources to add.')
parser.add_argument('-r', '--repo', default='.', help='The repository path '
                    'of the repo to use. Must be a filesystem path.')
parser.add_argument('-b', '--branch', default=None, help='The branch to '
                    'commit to.')
parser.add_argument('--author', default=None)
parser.add_argument('--author-time', default=now, type=int)
parser.add_argument('--author-timezone', default=localtz, type=parse_timezone)
parser.add_argument('--committer', default=None)
parser.add_argument('--commit-time', default=now, type=int)
parser.add_argument('--commit-timezone', default=localtz, type=parse_timezone)
parser.add_argument('-m', '--message', help='Commit message (utf-8 encoded).',
                    default=None)


class Source(object):
    _def_perm = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
    _exc_perm = _def_perm | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH

    def __init__(self, url):
        self.url = url


def _is_executable(path):
    mode = os.stat(path)[stat.ST_MODE]
    return mode & stat.S_IXUSR or mode & stat.S_IXGRP or mode & stat.S_IXOTH


class FilesystemSource(Source):
    scheme = 'file'

    def _handle_file(self, relpath, abspath):
        if os.path.isfile(abspath):
            with open(abspath, 'rb') as f:
                mode = stat.S_IFREG
                mode |= self._exc_perm if _is_executable(abspath)\
                                       else self._def_perm

                # tutorial says we can use from_file here - possibly wrong?
                return (relpath,
                       mode,
                       Blob.from_string(f.read()))
        elif os.path.islink(abspath):
            target = os.readlink(abspath)
            return (relpath,
                   stat.S_IFLNK,
                   Blob.from_string(target))
        else:
            raise RuntimeError('Can\'t handle %s' % abspath)

    def __iter__(self):
        path = self.url.path

        if os.path.isdir(path):
            for dirpath, dns, fns in os.walk(path):
                for fn in fns:
                    jpath = os.path.join(dirpath, fn)
                    relpath = os.path.relpath(jpath, path)
                    abspath = os.path.abspath(jpath)
                    yield self._handle_file(relpath, abspath)
        else:
            yield self._handle_file(
                os.path.basename(path), os.path.abspath(path)
            )


for source_class in [FilesystemSource]:
    SOURCES[source_class.scheme] = source_class


def main():
    args = parser.parse_args()

    # open repo
    repo = Repo(args.repo)
    config = repo.get_config_stack()
    ref_name = 'refs/heads/%s' % args.branch
    old_head = repo.refs[ref_name]

    for source_url in args.sources:
        src = SOURCES[source_url.scheme](source_url)
        sys.stderr.write(source_url.geturl())
        sys.stderr.write('\n')

        tree = Tree()
        for path, mode, blob in src:
            # add the blob
            repo.object_store.add_object(blob)

            # tree entry
            tree.add(path, mode, blob.id)

            sys.stderr.write(path)
            sys.stderr.write('\n')

        sys.stderr.write('\n')


        repo.object_store.add_object(tree)

        def get_user():
            return '%s <%s>' % (config.get('user', 'name'),
                                config.get('user', 'email'))

        commit = Commit()
        commit.parents = [old_head]

        commit.tree = tree.id
        commit.author = args.author or get_user()
        commit.committer = args.committer or get_user()

        commit.commit_time = args.commit_time
        commit.author_time = args.author_time

        commit.commit_timezone = args.commit_timezone[0]
        commit.author_timezone = args.author_timezone[0]

        commit.encoding = 'UTF-8'
        commit.message = args.message or 'Automatic commit using gittar.'

        repo.object_store.add_object(commit)

        # set ref
        repo.refs.set_if_equals(ref_name, old_head, commit.id)

        print commit.id

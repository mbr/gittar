#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from collections import OrderedDict
import time
from urlparse import urlparse
import sys

from dateutil.tz import tzlocal
from datetime import datetime

from dulwich.repo import Repo
from dulwich.objects import Tree, Commit, parse_timezone

from sources import SOURCES, MODE_TREE


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
                    metavar='SCHEME://...', help='Sources to add. Valid '
                    'schemes are %s' % ', '.join(
                        '%s://' % s for s in sorted(SOURCES.keys())
                    ))
parser.add_argument('-r', '--repo', default='.', help='The repository path '
                    'of the repo where files will be stored. Must be a '
                    'filesystem path.')
parser.add_argument('-b', '--branch', default=None, help='If given, create '
                    'branch with this name for commit. If the branch already '
                    'exists, make it a parent of the new commit and update '
                    'branch.')
parser.add_argument('--author', default=None, help='Author string in the '
                    'form of Author Name <author@email.invalid>. If not '
                    'given, use git defaults.')
parser.add_argument('--author-time', default=now, type=int, help='Author '
                    'timestamp, as a UNIX timestamp. Defaults to current '
                    'time.')
parser.add_argument('--author-timezone', default=localtz, type=parse_timezone,
                    help='Author timezone. Defaults to local timezone.')
parser.add_argument('--committer', default=None, help='Committer string in '
                    'the form of Committer Name <committer@email.invalid>. '
                    'If not given, use git defaults.')
parser.add_argument('--commit-time', default=now, type=int, help='Committer '
                    'timestamp, as a UNIX timestamp. Defaults to current '
                    'time.')
parser.add_argument('--commit-timezone', default=localtz, type=parse_timezone,
                    help='Author timezone. Defaults to local timezone.')
parser.add_argument('-m', '--message', help='Commit message. '
                    'If no message is given, one will be auto-generated.',
                    default='Automatic commmit using gittar.')
parser.add_argument('--encoding', default='UTF-8', help='Encoding for the '
                    'commit. Defaults to UTF-8.')


def main():
    args = parser.parse_args()

    # open repo
    repo = Repo(args.repo)
    config = repo.get_config_stack()
    ref_name = 'refs/heads/%s' % args.branch

    old_head = repo.refs[ref_name] if ref_name in repo.refs else None

    for source_url in args.sources:
        src = SOURCES[source_url.scheme](source_url)
        sys.stderr.write(source_url.geturl())
        sys.stderr.write('\n')

        root = OrderedDict()
        for path, mode, blob in src:
            # add the blob
            repo.object_store.add_object(blob)

            # tree entry
            node = root
            components = path.split('/')
            for c in components[:-1]:
                node = root.setdefault(c, OrderedDict())

            node[components[-1]] = (mode, blob.id)

            sys.stderr.write(path)
            sys.stderr.write('\n')

        sys.stderr.write('\n')

        # collect trees
        def store_tree(node):
            tree = Tree()

            for name in node:
                if isinstance(node[name], dict):
                    tree.add(name, MODE_TREE, store_tree(node[name]).id)
                else:
                    tree.add(name, *node[name])

            repo.object_store.add_object(tree)
            return tree

        tree = store_tree(root)

        def get_user():
            return '%s <%s>' % (config.get('user', 'name'),
                                config.get('user', 'email'))

        commit = Commit()

        if old_head:
            commit.parents = [old_head]

        commit.tree = tree.id
        commit.author = args.author or get_user()
        commit.committer = args.committer or get_user()

        commit.commit_time = args.commit_time
        commit.author_time = args.author_time

        commit.commit_timezone = args.commit_timezone[0]
        commit.author_timezone = args.author_timezone[0]

        commit.encoding = args.encoding
        commit.message = args.message

        repo.object_store.add_object(commit)

        # set ref
        if old_head:
            repo.refs.set_if_equals(ref_name, old_head, commit.id)
        else:
            repo.refs.add_if_new(ref_name, commit.id)

        print commit.id

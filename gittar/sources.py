#!/usr/bin/env python
# -*- coding: utf-8 -*-

from glob import glob
import os
import stat
import tarfile
from zipfile import ZipFile

from dulwich.objects import Blob


MODE_RFILE = stat.S_IFREG | \
             stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
MODE_XFILE = MODE_RFILE | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
MODE_LNK   = stat.S_IFLNK
MODE_TREE  = 0o0040000


def _is_executable(path):
    mode = os.stat(path)[stat.ST_MODE]
    return _executable_bits(mode)


def _executable_bits(mode):
    return mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class Source(object):
    @classmethod
    def create(cls, *args, **kwargs):
        """Factory method for creating a source.

        This allows creating more than once source from a single URI.

        :return: A generator of sources."""
        yield cls(*args, **kwargs)


class FilesystemSource(Source):
    scheme = 'file'

    def __init__(self, path):
        self.path = os.path.abspath(os.path.expanduser(path))
        self.isdir = os.path.isdir(self.path)

    def get_blob(self, path):
        if not self.isdir:
            abspath = os.path.abspath(self.path)
        else:
            abspath = os.path.join(os.path.dirname(self.path), path)

        if os.path.isfile(abspath):
            with open(abspath, 'rb') as f:
                # tutorial says we can use from_file here - possibly wrong?
                return (MODE_XFILE if _is_executable(abspath) else MODE_RFILE,
                        Blob.from_string(f.read()))
        elif os.path.islink(abspath):
            target = os.readlink(abspath)
            return (MODE_LNK,
                    Blob.from_string(target))
        else:
            raise RuntimeError('Can\'t handle %s' % abspath)

    def __iter__(self):
        if self.isdir:
            for dirpath, dns, fns in os.walk(self.path):
                for fn in fns:
                    jpath = os.path.join(dirpath, fn)
                    yield os.path.relpath(jpath, os.path.dirname(self.path))
        else:
            yield os.path.basename(self.path)

    @classmethod
    def create(cls, path):
        for path in glob(os.path.expanduser(path)):
            yield cls(path)


class ZipSource(Source):
    scheme = 'zip'

    def __init__(self, zipfn):
        self.zipfn = os.path.expanduser(zipfn)
        self.archive = ZipFile(self.zipfn)

    def __iter__(self):
        return iter(self.archive.namelist())

    def get_blob(self, name):
        with self.archive.open(name) as f:
            return MODE_RFILE, Blob.from_string(f.read())


class TarSource(Source):
    scheme = 'tar'

    def __init__(self, tarfn):
        self.tarfn = os.path.expanduser(tarfn)
        self.archive = tarfile.open(self.tarfn)

    def __iter__(self):
        for info in self.archive.getmembers():
            if info.isdir():
                continue
            yield info.name

    def get_blob(self, name):
        info = self.archive.getmember(name)
        if info.isfile() or info.islnk():
            target = info.name if info.isfile()\
                               else info.linkname
            mode = MODE_XFILE if _executable_bits(info.mode) else MODE_RFILE
            buf = self.archive.extractfile(target).read()
        elif info.issym():
            mode = MODE_LNK
            buf = info.linkname
        else:
            raise RuntimeError('Can\'t handle %s in %s' % (
                info.name, self.tarfile
            ))

        return mode, Blob.from_string(buf)


SOURCES = {cls.scheme: cls for cls in locals().values()
           if hasattr(cls, 'scheme')}

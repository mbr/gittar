#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import stat
import tarfile
from zipfile import ZipFile

from dulwich.objects import Blob


MODE_RFILE = stat.S_IFREG | \
             stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
MODE_XFILE = MODE_RFILE | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
MODE_LNK   = stat.S_IFLNK
MODE_TREE  = 0040000


def _is_executable(path):
    mode = os.stat(path)[stat.ST_MODE]
    return _executable_bits(mode)


def _executable_bits(mode):
    return mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class Source(object):
    def __init__(self, url):
        self.url = url


class FilesystemSource(Source):
    scheme = 'file'

    def _handle_file(self, relpath, abspath):
        if os.path.isfile(abspath):
            with open(abspath, 'rb') as f:
                # tutorial says we can use from_file here - possibly wrong?
                return (relpath,
                       MODE_XFILE if _is_executable(abspath) else MODE_RFILE,
                       Blob.from_string(f.read()))
        elif os.path.islink(abspath):
            target = os.readlink(abspath)
            return (relpath,
                   MODE_LNK,
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


class ZipSource(Source):
    scheme = 'zip'

    def __iter__(self):
        with ZipFile(self.url.path) as archive:
            for name in archive.namelist():
                with archive.open(name) as f:
                    yield name, MODE_RFILE, Blob.from_string(f.read())


class TarSource(Source):
    scheme = 'tar'

    def __iter__(self):
        with tarfile.open(self.url.path) as archive:
            for info in archive.getmembers():
                if info.isdir():
                    continue
                elif info.isfile() or info.islnk():
                    target = info.name if info.isfile()\
                                       else info.linkname
                    mode = MODE_XFILE if _executable_bits(info.mode)\
                                          else MODE_RFILE
                    buf = archive.extractfile(target).read()
                elif info.issym():
                    mode = MODE_LNK
                    buf = info.linkname
                else:
                    raise RuntimeError('Can\'t handle %s in %s' % (
                        info.name, self.url.geturl()
                    ))

                yield info.name, mode, Blob.from_string(buf)


SOURCES = {cls.scheme : cls for cls in locals().values()
           if hasattr(cls, 'scheme')}

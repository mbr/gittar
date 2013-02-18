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
    pass


class FilesystemSource(Source):
    scheme = 'file'

    def __init__(self, path):
        self.path = os.path.expanduser(path)

    def get_blob(self, relpath):
        abspath = os.path.abspath(relpath)
        if relpath == self.path:
            relpath = os.path.basename(relpath)

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
        if os.path.isdir(self.path):
            for dirpath, dns, fns in os.walk(self.path):
                for fn in fns:
                    jpath = os.path.join(dirpath, fn)
                    yield os.path.relpath(jpath, self.path)
        else:
            yield self.path


class ZipSource(Source):
    scheme = 'zip'

    def __init__(self, zipfile):
        self.zipfile = os.path.expanduser(zipfile)

    def __iter__(self):
        with ZipFile(self.zipfile) as archive:
            for name in archive.namelist():
                with archive.open(name) as f:
                    yield name, MODE_RFILE, Blob.from_string(f.read())


class TarSource(Source):
    scheme = 'tar'

    def __init__(self, tarfile):
        self.tarfile = os.path.expanduser(tarfile)

    def __iter__(self):
        with tarfile.open(self.tarfile) as archive:
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
                        info.name, self.tarfile
                    ))

                yield info.name, mode, Blob.from_string(buf)


SOURCES = {cls.scheme : cls for cls in locals().values()
           if hasattr(cls, 'scheme')}

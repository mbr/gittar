#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='gittar',
    version='0.2.1',
    description='The inverse of git archive. Adds a new commit from an archive'
                'or the filesystem.',
    long_description=read('README.rst'),
    author='Marc Brinkmann',
    author_email='git@marcbrinkmann.de',
    url='http://github.com/mbr/gittar',
    license='MIT',
    packages=find_packages(exclude=['test']),
    install_requires=['dulwich', 'python-dateutil'],
    entry_points={
        'console_scripts': [
            'gittar = gittar:main',
        ],
    }
)

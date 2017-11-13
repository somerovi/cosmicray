# -*- coding: utf-8 -*-


import codecs
import collections
import os


QueryParam = collections.namedtuple('QueryParam', ['name', 'value', 'required'])


def param(name, value=None, required=False):
    return QueryParam(name=name, value=value, required=required)


def user_home(*args):
    home = os.path.expanduser("~")
    return os.path.join(home, *args)


def cosmicray_home(*args):
    directory = user_home('.cosmicray')
    if not os.path.exists(directory):
        os.makedirs(directory)
    return os.path.join(directory, *args)


def write_artifact_file(fpath, data):
    with codecs.open(fpath, 'w', 'utf-8') as fobj:
        fobj.write(data)


def read_artifact_file(fpath):
    with codecs.open(fpath, 'r', 'utf-8') as fobj:
        return fobj.read()

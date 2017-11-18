# -*- coding: utf-8 -*-


import codecs
import collections
import os


USER_DIR = '~'
COSMICRAY_DIR = '.cosmicray'


Param = collections.namedtuple(
    'Param', ['name', 'default', 'required', 'enums', 'validate'])


def param(name, default=None, required=False, enums=None, validate=None):
    return Param(name=name, default=default, required=required,
                 enums=enums, validate=validate)


class CachedArtifact(object):
    __cached = {}

    @classmethod
    def cache(cls, function):
        def decorate(fpath, *args, **kwargs):
            if not fpath in cls.__cached:
                cls.__cached[fpath] = function(fpath, *args, **kwargs)
            return cls.__cached[fpath]
        return decorate

    @classmethod
    def bust(cls, function):
        def decorate(fpath, *args, **kwargs):
            try:
                del cls.__cached[fpath]
            except KeyError:
                pass
            return function(fpath, *args, **kwargs)
        return decorate


def user_home(*args):
    home = os.path.expanduser(USER_DIR)
    return os.path.join(home, *args)


def cosmicray_home(*args):
    directory = user_home(COSMICRAY_DIR)
    if not os.path.exists(directory):
        os.makedirs(directory)
    return os.path.join(directory, *args)


@CachedArtifact.bust
def write_artifact_file(fpath, data):
    with codecs.open(fpath, 'w', 'utf-8') as fobj:
        fobj.write(data)


@CachedArtifact.cache
def read_artifact_file(fpath):
    with codecs.open(fpath, 'r', 'utf-8') as fobj:
        return fobj.read()

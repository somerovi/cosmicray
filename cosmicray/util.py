# -*- coding: utf-8 -*-


import codecs
import collections
import copy
import functools
import os
import threading
import time


COSMICRAY_DIR = '~/.cosmicray'


class RequestTemplate(object):

    DEFAULTS = {
        'headers': collections.OrderedDict,
        'params': dict,
        'urlargs': dict,
        'extra': dict
    }
    __slots__ = (
        'auth',
        'data',
        'files',
        'headers',
        'json',
        'params',
        'extra',
        'authenticator',
        'domain',
        'path',
        'method',
        'urlargs',
        'model_cls',
        'route'
    )

    def __init__(self, args=None, **kwargs):
        for attr in RequestTemplate.__slots__:
            default = RequestTemplate.DEFAULTS.get(attr)
            setattr(self, attr, None if not default else default())
        self.update(args, **kwargs)

    def items(self):
        '''Returns iterator of attr and value pairs. The returned value is a copy'''
        return ((attr, copy.deepcopy(getattr(self, attr)))
                for attr in RequestTemplate.__slots__)

    def copy(self):
        '''Returns new instance of :class:`RequestTemplate` with a copy of all fields'''
        return self.__class__(self.items())

    def update(self, args=None, **kwargs):
        '''Soft updates based on the given arguments. Mapping objects will be
        merged rather than overwritten'''
        if args:
            self._update_from_sequence(args)
        self._update_from_map(kwargs)

    def override(self, args=None, **kwargs):
        '''Updates based on the given arguments. Mapping objects will be overwritten'''
        if args:
            self._update_from_sequence(args, override=True)
        self._update_from_map(kwargs, override=True)

    def _update_from_sequence(self, arg, override=False):
        for attr, value in arg:
            self._set_attr(attr, value, {}, override)

    def _update_from_map(self, kwargs, override=False):
        for attr, value in kwargs.items():
            self._set_attr(attr, value, {}, override)

    def _set_attr(self, attr, arg, kwargs, override):
        '''
        Sets the value for the given attribute
        :param attr: the attribute name
        :param arg: value or sequence
        :param kwargs: Mapping
        :param override: If the attribute being set is a mapping, then if override is True,
            it will discard existing values. Otherwise, it updates the existing mapping
        '''
        try:
            if not override:
                obj = getattr(self, attr)
                try:
                    obj.update(arg or {}, **kwargs)
                    arg = obj
                except AttributeError:
                    pass
            setattr(self, attr, arg)
        except AttributeError:
            self.extra[attr] = arg

    def _set_attr_chain(self, attr):
        '''All attributes in the :class:`RequestTemplate`.__slots__ have a
        special setter that can be used to set the value of the attribute and
        return the instance of itself to chain together calls.
        The setter is of the form: set_{attr name}
        '''
        def wrapper(arg=None, override=False, **kwargs):
            self._set_attr(attr, arg, kwargs, override=override)
            return self
        return wrapper

    def __getattribute__(self, attr):
        if attr.startswith('set_'):
            _, attr = attr.split('set_')
            if attr in RequestTemplate.__slots__:
                return self._set_attr_chain(attr)
        elif attr in ['urlargs', 'params']:
            # Filter out none values from urlargs
            obj = object.__getattribute__(self, attr)
            if obj:
                return dict((k, v) for k, v in obj.items() if v is not None)
            return obj
        return object.__getattribute__(self, attr)


class CachedArtifact(object):
    '''
    Provides simple, thread-safe, decorators to cache frequently accessed files
    and update the cache automatically if files get written to.
    '''

    __cached = {}
    _lock = threading.Lock()

    @classmethod
    def read(cls, function):
        '''Returns cached value for the given path, otherwise reads from disk'''
        @functools.wraps(function)
        def decorate(fpath, serializer=None):
            while CachedArtifact._lock.locked():
                time.sleep(0.001)
            if not fpath in cls.__cached:
                cls.__cached[fpath] = function(fpath, serializer)
            return cls.__cached[fpath]
        return decorate

    @classmethod
    def write(cls, function):
        '''Writes data for the given path to disk and updates the cache'''
        @functools.wraps(function)
        def decorate(fpath, data, serializer=None):
            with CachedArtifact._lock:
                try:
                    del cls.__cached[fpath]
                except KeyError:
                    pass
                cls.__cached[fpath] = function(fpath, data, serializer)
                return cls.__cached[fpath]
        return decorate


def _keys_to_lower(obj):
    return dict((k.lower(), v) for k, v in obj.items())


class Config(object):
    '''lettercase-agnostic key-value store'''
    def __init__(self, args=None,  **kwargs):
        self._config = {}
        self.update(args, **kwargs)

    def get(self, key, default=None):
        '''Return value for the given key or default if key not found'''
        return self._config.get(key.lower(), default)

    def setdefault(self, key, default):
        '''Set default value for a key if it doesn't exist'''
        return self._config.setdefault(key.lower(), default)

    def keys(self):
        return self._config.keys()

    def getcopy(self, key, default=None):
        '''Returns a copy of the value for the given key or default if key not found'''
        return copy.deepcopy(self.get(key, default))

    def __getitem__(self, key):
        return self._config[key.lower()]

    def __setitem__(self, key, value):
        self._config[key.lower()] = value

    def __delitem__(self, key):
        del self._config[key.lower()]

    def update(self, args=None, **kwargs):
        '''Updates key-value store'''
        self._config.update(
            _keys_to_lower(args or {}), **_keys_to_lower(kwargs))

    def copy(self):
        '''Return instance of :class:`Config` with copy of the objects data'''
        return Config(copy.deepcopy(self._config))

    def __repr__(self):
        return '<Config {!r}>'.format(self._config)

    def get_dict(self):
        return self._config

    def set_dict(self, obj):
        self._config = obj

    def del_dict(self):
        del self._config

    dict = property(get_dict, set_dict, del_dict)


def create_home_dir(name=None, root_path=None):
    '''Creates a home directory

    :param name: Optional directory name.
    :param root_path: Alternative root path. Default: ~/.cosmicray
    :returns: home directory path
    '''
    if root_path is None:
        root_path = os.path.expanduser(COSMICRAY_DIR)
    directory = os.path.join(root_path, name or '')
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory


@CachedArtifact.write
def write_artifact_file(fpath, data, serializer=None):
    '''Writes serialized data to the given file path'''
    with codecs.open(fpath, 'w', 'utf-8') as fobj:
        fobj.write(serializer(data) if serializer else data)
    return data


@CachedArtifact.read
def read_artifact_file(fpath, serializer=None):
    '''Reads and deserializes contents of data to the given file path'''
    with codecs.open(fpath, 'r', 'utf-8') as fobj:
        data = fobj.read()
        return serializer(data) if serializer else data

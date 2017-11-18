# -*- coding: utf-8 -*-


import copy
import os


def _keys_to_upper(obj):
    return dict((k.upper(), v) for k, v in obj.items())


class Config(object):
    def __init__(self, data=None,  **kwargs):
        self._config = {}
        self.update(data, **kwargs)

    def get(self, key, default=None):
        return self._config(key.upper(), default)

    def getenv(self, key, default=None):
        return os.environ.get(key.upper(), default)

    def getcopy(self, key):
        value = self[key]
        return copy.deepcopy(value)

    def __getitem__(self, key):
        return self._config[key.upper()]

    def __setitem__(self, key, value):
        self._config[key.upper()] = value

    def __delitem__(self, key):
        del self._config[key.upper()]

    def update(self, from_dict=None, **kwargs):
        self._config.update(
            _keys_to_upper(from_dict or {}), **_keys_to_upper(kwargs))

    def copy(self):
        return Config(copy.deepcopy(self._config))

    def __repr__(self):
        return '<Config {!r}>'.format(self._config)

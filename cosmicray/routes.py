# -*- coding: utf-8 -*-

import collections
import inspect
import json
import os
import string

import requests
import six

from . import util


STORE_ITEMS = ['auth', 'domain', 'headers', 'params', 'urlargs', 'extra']


class Cosmicray(object):
    '''
    :param name: App name and User-Agent header
    :param domain: Domain name. Default: http://localhost:8080
    :param home_dir: Apps home directory to store artifact files, such as credentials
        the full path for the home directory will be ``~/.cosmicray/{name}``

    Usage::

        >>> api = Cosmicray('myapp', 'http://mydomain.com')
        >>> api.configure(headers={'Content-Type': 'application/json'})

    '''
    def __init__(self, name, domain='http://localhost:8080', home_dir=None):
        self.name = name
        self.routes = []
        self.config = util.Config({
            'debug': False,
            'raise_for_status': True,
            'disable_validation': False,
            'home_dir': util.create_home_dir(name, root_path=home_dir)
        })
        self.config['config_filename'] = self.home_dir('config')
        self.tpl = util.RequestTemplate(
            domain=domain, headers={'User-Agent': self.name})
        self.session = requests.Session()

    def home_dir(self, *args):
        '''Returns home directory path joined with the given argument sequence'''
        return os.path.join(self.config['home_dir'], *args)

    def cache_dir(self, *args):
        path = self.home_dir('cache')
        if not os.path.exists(path):
            os.makedirs(path)
        return os.path.join(path, *args)

    def route(self, path, methods, params=None, urlargs=None, headers=None):
        '''
        Decorates a function that needs to accept :class:`requests.Response <Response>` object
        as the only argument, process the response and return the result (ex. return json).

        :param path: Uri of type str or string formatter.
        :param methods: list of all allowed methods
        :param params: list of :class:`cosmicray.Param` query parameters
        :param urlargs: list of :class:`cosmicray.Param`
        :param headers: mapping representing request headers
        :returns: decorator

        Usage::

            >>> api = Cosmicray('myapp', 'http://mydomain.com')
            >>> @api.route('/some/path')
            ... def some_path(response):
            ...     return response.json()
            ...

        '''
        route = Route(path, methods, params, urlargs, headers, app=self)
        self.routes.append(route)
        return route.response_handler_decorator

    def configure(self, config=None, **kwargs):
        '''
        :param config: Mapping for general app settings
        :param \*\*kwargs: Application wide request configurations
             domain: Domain name
             headers: Mapping of http headers
             urlargs: Mapping of url formatting arguments
             params: Mapping of query parameters
             authenticator: Callback for request authentication
             auth: Basic auth
             &rest: Keyword arguments for `requests`
        '''
        self.tpl.update(**kwargs)
        self.config.update(config)

    def get_config(self, key):
        '''Return config value for the given key'''
        try:
            return getattr(self.tpl, key.lower())
        except AttributeError:
            try:
                return self.config[key]
            except KeyError:
                try:
                    return self.tpl.extra[key]
                except KeyError:
                    pass

    def store_configurations(self):
        ''''Save config to file'''
        configs = {
            'config': self.config.dict,
            'request_config': dict(
                (k, v) for k, v in self.tpl.items() if k in STORE_ITEMS),
        }
        util.write_artifact_file(
            self.get_config('config_filename'), configs, json.dumps)

    def load_configurations(self):
        ''''Load config from file'''
        fpath = self.get_config('config_filename')
        if os.path.exists(fpath):
            configs = util.read_artifact_file(fpath, json.loads)
            self.config.update(configs.get('config'))
            self.tpl.update(**configs.get('request_config', {}))

    def __repr__(self):
        return '<{app} app for {name}>'.format(
            app=self.__class__.__name__, name=self.name)


class Route(object):
    '''Defines properties of a route

    :param path: Uri of type str or string formatter.
    :param methods: list of all allowed methods
    :param params: list of :class:`cosmicray.Param` query parameters
    :param urlargs: list of :class:`cosmicray.Param`
    :param headers: mapping representing request headers
    '''

    def __init__(self, path, methods, params, urlargs, headers, app=None):
        self.app = app
        self.path = path
        self.methods = methods
        self.params = params
        self.urlargs = urlargs
        self.headers = headers
        self.response_handler = None

    def response_handler_decorator(self, response_handler):
        '''Decorates a function and turns it into response handler'''
        self.response_handler = response_handler
        return self

    def __eq__(self, obj):
        if isinstance(obj, Route):
            return self.path == obj.path
        elif isinstance(obj, six.string_types):
            return self.path == obj
        raise TypeError('Incompatible type: {}'.format(type(obj)))

    def __call__(self, model_cls=None, **kwargs):
        request = Request(
            route=self, model_cls=model_cls,
            args=self.app.tpl.items(),
            path=self.path, headers=self.headers)
        request.update(**kwargs)
        return request

    def get_config(self, key):
        '''Return config value for the given key'''
        return self.app.get_config(key)

    def __repr__(self):
        return '<{name} for {path!r}>'.format(
            name=self.__class__.__name__, path=self.path)


class Request(util.RequestTemplate):
    __doc__ = ('''
    :param route: instance of :class:`Route`
    :param model_cls: class that implements `_make` method
    :param args: sequence of key-value pairs to initialize the request with
    :param \*\*kwargs: keyword arguments to initialize the request with

    Any parameters given to :class:`Request` can be updated with :class:`Request.update` OR
    completly overwritten with :class:`Request.override`

    :class:`Request` provides special setter methods that set the given attribute and return the instance of itself to chain together calls:
    {}
    '''.format('\n'.join('\t\t:class:`Request.set_{}`\n'.format(attr)
                       for attr in util.RequestTemplate.__slots__)))
    __slots__ = ()

    def __init__(self, route, model_cls, args=None, **kwargs):
        super(Request, self).__init__(args, **kwargs)
        self.route = route
        self.model_cls = model_cls

    def is_request_for(self, *routes):
        '''Returns True if :class:`Request`.route is in the given sequence of routes'''
        return any(self.route == route for route in routes)

    def handle_response(self, response):
        '''Calls the routes response handler with the given response and maps the model to the given result'''
        expected_args = inspect.getargspec(self.route.response_handler).args
        args = [self, response] if len(expected_args) == 2 else [response]
        return self.map_model(self.route.response_handler(*args))

    def map_model(self, response):
        '''Calls :class:`Request`.model_cls._make method if a model was provided, otherwise returns the given response'''
        if self.model_cls is not None and response is not None:
            _make = getattr(self.model_cls, '_make')
            try:
                return _make(response)
            except TypeError:
                return map(_make, response)
        return response

    def authenticate(self):
        '''Authenticates the request, if :class:`Request`.authenticator call back is provided'''
        if self.authenticator:
            return self.authenticator(self)
        return self

    def validate(self):
        '''Validates method, query parameters, and urlarg parameters'''
        if not self.route.get_config('disable_validation'):
            if self.method not in self.route.methods:
                raise TypeError('Method {!r} is not supported by {!r}'.format(
                    self.method, self.route))

            self.params = self._validate_params(self.params, self.route.params)
            self.urlargs = self._validate_params(self.urlargs, self.route.urlargs)
        return self

    def _validate_params(self, actual, expected):
        if expected:
            for param in expected:
                value = param.validate(actual.get(param.name), context=self)
                actual[param.name] = value
        return actual

    @property
    def url(self):
        '''combines domain and path and formats the final result with urlargs'''
        uri = DefaultUrlFormatter().format(self.path, **self.urlargs)
        return '{}/{}'.format(self.domain.rstrip('/'), uri.lstrip('/'))

    def _log(self, response):
        '''Log the request and response'''
        if self.route.get_config('debug'):
            obj = json.dumps({
                'request': {
                    'url': response.url,
                    'method': response.request.method,
                    'headers': dict(response.request.headers),
                    'body': str(response.request.body or "")
                },
                'response': {
                    'headers': dict(response.headers),
                    'status_code': response.status_code,
                    'body': response.text,
                    'duration': response.elapsed.total_seconds()
                }
            })
            print(obj)

    def send(self):
        '''Makes request and returns the result of the response being handled by the response handler'''
        response = self.route.app.session.request(
            self.method.lower(), self.url, headers=self.headers, params=self.params,
            data=self.data, files=self.files, json=self.json,
            auth=self.auth, **self.extra)
        self._log(response)
        if self.route.get_config('raise_for_status'):
            response.raise_for_status()
        return self.handle_response(response)

    def get(self):
        '''GET request'''
        return self.set_method('GET').validate().authenticate().send()

    def delete(self):
        '''DELETE request'''
        return self.set_method('DELETE').validate().authenticate().send()

    def post(self):
        '''POST request'''
        return self.set_method('POST').validate().authenticate().send()

    def put(self):
        '''PUT request'''
        return self.set_method('PUT').validate().authenticate().send()

    def head(self):
        '''HEAD request'''
        return self.set_method('HEAD').validate().authenticate().send()

    def options(self):
        '''OPTIONS request'''
        return self.set_method('OPTIONS').validate().authenticate().send()

    def __repr__(self):
        return '<Request for {}>'.format(self.route.path)


class DefaultUrlFormatter(string.Formatter):

    def get_value(self, key, args, kwargs):
        try:
            return kwargs[key]
        except KeyError as error:
            return ''
        return Formatter.get_value(key, args, kwargs)


class Param(object):
    '''Used for query parameters and urlargs to validate and specify default values

    :param name: the parameters name
    :param default: Specify default value for the parameter. The default may be a
        callback that accepts two arguments, an object and context, where object
        is the given value for the parameter and context is :class:`Request`
    :param required: boolean to indicate if parameter is required
    :param options: Sequence of options that the parameter can have
    '''
    def __init__(self, name, default=None, required=False, options=None):
        self.name = name
        self.default = default
        self.required = required
        self.options = options

    def validate(self, obj, context):
        '''Validates the parameter and if it's invalid raises an exception

        :param obj: value provided for the parameter
        :param context: :class:`Request` instance
        :returns: value for the parameter
        '''
        if callable(self.default):
            value = self.default(obj, context)
        else:
            value = self.default if obj is None else obj

        if self.required and not value:
            raise TypeError('Required parameter {!r} is None or not provided'.format(self.name))

        if self.options and value not in self.options:
            raise TypeError('Invalid value for parameter {!r}: {!r}'.format(self.name, value))

        return value

    def __repr__(self):
        return '{name}({args})'.format(
            name=self.__class__.__name__, args=', '.join(
            ['{}={!r}'.format((attr, getattr(self, attr)))
             for attr in ['name', 'default', 'required', 'options']]))
